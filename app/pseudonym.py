"""Pseudonymisation: identities never leave the machine.

The LLM sees the question with company names -> {C1}, explicit INNs -> {INN1}, broker codes -> {B1},
plus a block saying how many participants each placeholder matched. It writes SQL with
{C1_INNS}, {INN1}, {B1} tokens; `substitute_sql` puts the real values back before execution.
`unmask` restores the user's own wording in interpretation / answer templates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.entities import CompanyHit, EntityResolver, Resolution, extract_phrases
from app.normalize import company_key

_INN_RE = re.compile(r"(?<![\d.,])\d{9}(?![\d.,])")
_BROKER_CODE_RE = re.compile(r"\bBK\s?(\d{3})\b", re.I)
_TOKEN_RE = re.compile(r"\{(C\d+_INNS|C\d+_KEY|C\d+|INN\d+|B\d+)\}")
_QUOTED_TOKEN_RE = re.compile(r"'?\{(C\d+_INNS|C\d+_KEY|C\d+|INN\d+|B\d+)\}'?")  # tokens are always text: we add the quotes


@dataclass(frozen=True)
class Masked:
    question: str                       # what the LLM sees
    entity_block: str                   # placeholder legend for the planner
    mapping: dict[str, str]             # placeholder -> real text as the user wrote it
    inns: dict[str, list[str]]          # {C1} -> candidate INNs
    companies: dict[str, list[CompanyHit]] = field(default_factory=dict)
    unmatched: list[str] = field(default_factory=list)   # phrases that matched no participant (left unmasked)
    leaked: list[str] = field(default_factory=list)      # phrases we could not locate in the text

    def substitute_sql(self, sql: str) -> str:
        def repl(m: re.Match) -> str:
            token = m.group(1)
            if token.endswith("_INNS"):
                inns = self.inns.get("{" + token[:-5] + "}", [])
                return ", ".join(f"'{i}'" for i in inns) or "''"
            if token.endswith("_KEY"):
                return "'" + _sql_quote(company_key(self.mapping.get("{" + token[:-4] + "}", ""))) + "'"
            return "'" + _sql_quote(self.mapping.get("{" + token + "}", "")) + "'"
        return _QUOTED_TOKEN_RE.sub(repl, sql)

    def unmask(self, text: str) -> str:
        for placeholder, real in sorted(self.mapping.items(), key=lambda kv: -len(kv[0])):
            text = text.replace(placeholder, real)
        return text


def _sql_quote(value: str) -> str:
    return value.replace("'", "''")


def _locate(question: str, phrase: str) -> re.Match | None:
    """Find the phrase in the original text, tolerant to quotes, apostrophes and legal forms around it."""
    words = [re.escape(w) for w in phrase.split()]
    if not words:
        return None
    pattern = r"[«\"“„']?" + r"[\s'‘’`-]+".join(words) + r"[»\"”']?"
    return re.search(pattern, question, re.I)


class Pseudonymizer:
    def __init__(self, resolver: EntityResolver) -> None:
        self.resolver = resolver

    def mask(self, question: str, resolution: Resolution) -> Masked:
        mapping: dict[str, str] = {}
        inns: dict[str, list[str]] = {}
        companies: dict[str, list[CompanyHit]] = {}
        unmatched: list[str] = []
        leaked: list[str] = []
        legend: list[str] = []
        masked = question

        for i, inn in enumerate(resolution.inns, 1):
            ph = f"{{INN{i}}}"
            mapping[ph] = inn
            masked = masked.replace(inn, ph)
            legend.append(f"- {ph}: an INN given explicitly (use inn = '{ph}' or seller_inn/buyer_inn = '{ph}')")

        b = 0
        for m in list(_BROKER_CODE_RE.finditer(question)):
            b += 1
            ph = f"{{B{b}}}"
            code = f"BK{m.group(1)}"
            mapping[ph] = code
            masked = masked.replace(m.group(0), ph)
            legend.append(f"- {ph}: a broker code (use seller_broker = '{ph}' OR buyer_broker = '{ph}')")

        c = 0
        phrases = extract_phrases(question) or self.resolver.guess_phrases(question)
        for phrase in phrases:
            kind, payload = self.resolver.match_phrase(phrase)
            if kind == "broker":
                b += 1
                ph = f"{{B{b}}}"
                mapping[ph] = str(payload)
                legend.append(f"- {ph}: a broker named in the question (use seller_broker = '{ph}' OR buyer_broker = '{ph}')")
            else:
                c += 1
                ph = f"{{C{c}}}"
                mapping[ph] = phrase
                if kind == "companies":
                    hits = list(payload)  # type: ignore[arg-type]
                    companies[ph] = hits
                    inns[ph] = [h.inn for h in hits]
                    legend.append(
                        f"- {ph}: a company named in the question; {len(hits)} participant(s) matched -> "
                        f"filter with inn IN ({ph}_INNS) (or seller_inn/buyer_inn IN ({ph}_INNS)); "
                        f"SELECT inn and name so each match is shown separately")
                else:
                    # not in our data -> not an identity we hold; leave the wording, just tell the planner
                    c -= 1
                    del mapping[ph]
                    unmatched.append(phrase)
                    legend.append(f"- phrase '{phrase}' matched no participant or broker (it may not be a name at all)")
                    continue
            loc = _locate(masked, phrase)
            if loc:
                masked = masked[:loc.start()] + ph + masked[loc.end():]
            else:
                leaked.append(phrase)

        block = ""
        if legend:
            block = ("PLACEHOLDERS (real names/INNs are substituted by the server; write the tokens literally in SQL):\n"
                     + "\n".join(legend))
        return Masked(question=masked, entity_block=block, mapping=mapping, inns=inns, companies=companies,
                      unmatched=unmatched, leaked=leaked)
