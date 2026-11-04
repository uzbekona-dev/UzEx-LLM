"""Deterministic entity resolution done in code BEFORE the LLM writes SQL.

Products, companies (participants), brokers, INNs and deal numbers are found in the
question with rapidfuzz / regexes against the static dictionaries and the DB, so the
planner only chooses among verified candidates instead of guessing names or codes.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field

from rapidfuzz import fuzz, process

from app.dictionaries import PRODUCTS, REGIONS
from app.normalize import company_key, translit

MAX_PRODUCT_HITS = 3
PRODUCT_MIN_SCORE = 80
COMPANY_LIMIT = 5
COMPANY_CUTOFF = 85
BROKER_CUTOFF = 90
MAX_PHRASES = 2
MAX_SUBSTRING_HITS = 10  # a key found as substring in more participants than this is too generic


@dataclass(frozen=True)
class ProductHit:
    tnved: str
    name_ru: str
    name_uz: str
    score: int
    matched: str


@dataclass(frozen=True)
class CompanyHit:
    inn: str
    name: str
    region: str | None
    score: int


@dataclass(frozen=True)
class Resolution:
    products: list[ProductHit]
    companies: list[CompanyHit]
    brokers: list[str]
    inns: list[str]
    deal_nos: list[int]
    unmatched_phrases: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.products or self.companies or self.brokers or self.inns or self.deal_nos
                    or self.unmatched_phrases)

    def prompt_block(self) -> str:
        if self.is_empty():
            return ""
        lines = ["RESOLVED ENTITIES (use these, do not guess others):"]
        if self.products:
            lines.append("- products: " + " ; ".join(
                f"{p.tnved} {p.name_ru} / {p.name_uz} (matched '{p.matched}', {p.score})" for p in self.products))
        if self.companies:
            lines.append("- companies: " + " ; ".join(
                f"{c.inn} {c.name}" + (f" ({c.region})" if c.region else "") for c in self.companies))
        if self.inns:
            lines.append("- INNs given explicitly: " + ", ".join(self.inns))
        if self.brokers:
            lines.append("- brokers: " + ", ".join(self.brokers))
        if self.deal_nos:
            lines.append("- deal numbers: " + ", ".join(str(n) for n in self.deal_nos))
        for phrase in self.unmatched_phrases:
            lines.append(f"- company phrase '{phrase}' matched no participant")
        return "\n".join(lines)


# ----------------------------------------------------------------------------- regexes
_INN_RE = re.compile(r"(?<![\d.,])\d{9}(?![\d.,])")
_LONG_NUMBER_RE = re.compile(r"(?<![\d.,])\d{6,}(?![\d.,])")
_BROKER_CODE_RE = re.compile(r"\bBK\s?(\d{3})\b", re.I)
_QUOTED_RE = re.compile(r"[«\"“„]([^»\"”“„]{2,80})[»\"”“]|'([^']{3,80})'")
_WORD_RE = re.compile(r"[^\W\d_][\w'‘’`-]*")
_LEGAL_FORM_RE = re.compile(
    r"^(mchj|ooo|aj|ok|xk|qk|ip|yatt|chp|mas uliyati cheklangan jamiyati|masuliyati cheklangan jamiyati)$")
_LEGAL_FORMS_RAW = {"mchj", "ooo", "aj", "ok", "xk", "qk", "chp", "ip", "yatt", "мчж", "ооо", "аж", "хк", "қк", "чп", "ип",
                    "ак", "ok", "ao", "ао"}
_BROKER_WORD_RE = re.compile(r"([\w'‘’-]+)\s+(?:broker|брокер)\w*", re.I)

# words that are never a company name on their own (translit form)
_STOP_WORDS = frozenset("""
qancha nechta qaysi qanday kim kimga kimdan nima nimaga qachon qayerda qayer necha barcha hamma eng
skolko kakoy kakaya kakie kakoe kakuyu kakogo kto komu chto gde kogda vse vsego samiy samaya
sotgan sotdi sotilgan sotib olgan oldi olingan tuzgan tuzilgan tuzdi bitim bitimlar sdelka sdelki sdelok
kompaniya kompaniyasi kompaniyaning kompaniyalar firma firmasi korxona korxonasi tashkilot
tovar tovari tovarlar mahsulot mahsuloti mahsulotlar produkt produktsiya
broker brokeri brokerlar brokerlari inn stir jami itogo umumiy summa hajm hajmi narx narxi
yil yili yilda yilgi god godu goda mln mlrd ming ming so m som sum dollar dollor usd uzs
sotuvchi xaridor prodavets pokupatel birja uzex spot forvard forward fyuchers
yanvar fevral mart aprel may iyun iyul avgust sentyabr oktyabr noyabr dekabr
""".split())
_REGION_WORDS = frozenset(w for _, _, aliases in REGIONS for a in aliases for w in translit(a).split())
_GENERIC_PRODUCT_WORDS = frozenset(
    ["tovar", "tovari", "tovarlar", "mahsulot", "mahsuloti", "mahsulotlar", "produkt", "produktsiya"])
_UZ_SUFFIXES = ("larning", "larni", "lardan", "larga", "lar", "ning", "ni", "dan", "ga", "da", "i")
_SHORT_ALIAS_STOP = frozenset(["tuzgan", "tuzdi", "tuzadi", "misol", "unga", "unda", "uni", "ipak", "risk", "riski"])


# ----------------------------------------------------------------------------- products
def _product_index() -> list[tuple[str, str]]:
    """[(alias_key, tnved)] - every RU/UZ canonical name and alias, translit'ed, deduplicated."""
    seen: set[tuple[str, str]] = set()
    index: list[tuple[str, str]] = []
    for tnved, (ru, uz, aliases) in PRODUCTS.items():
        for raw in [ru, uz, *aliases]:
            for part in re.split(r"\s*/\s*|\s*\(|\)", raw):
                key = translit(part)
                if key and (key, tnved) not in seen and key not in _GENERIC_PRODUCT_WORDS:
                    seen.add((key, tnved))
                    index.append((key, tnved))
    return index


_PRODUCT_INDEX = _product_index()


def _token_variants(token: str) -> set[str]:
    """Token plus Uzbek-suffix-stripped forms: 'paxtani' -> {'paxtani', 'paxta'}."""
    out = {token}
    for suf in _UZ_SUFFIXES:
        if token.endswith(suf) and len(token) - len(suf) >= 3:
            out.add(token[: -len(suf)])
    return out


def _alias_score(alias: str, tokens: list[str], ngrams: dict[int, list[str]]) -> int:
    n_words = alias.count(" ") + 1
    if n_words > 1:
        return max((int(fuzz.ratio(ng, alias)) for ng in ngrams.get(n_words, [])), default=0)
    best = 0
    for tok in tokens:
        if tok in _SHORT_ALIAS_STOP:
            continue
        if any(v == alias for v in _token_variants(tok)):
            return 100
        if len(alias) <= 3:
            if len(alias) == 3 and tok.startswith(alias) and len(tok) == len(alias) + 1:
                best = max(best, 90)
            continue
        if len(alias) >= 5 and tok.startswith(alias):
            return 100
        extra = 0 if len(alias) == 4 else 2  # 'muki'~'muka', 'saxara'~'saxar' (RU/UZ inflection)
        if tok[: len(alias) - 1] == alias[:-1] and len(tok) <= len(alias) + extra:
            best = max(best, 90)
            continue
        if len(alias) >= 6 and abs(len(tok) - len(alias)) <= 1 and tok[: len(alias) - 2] == alias[:-2]:
            best = max(best, 85)  # RU fleeting vowel: 'xlopka' ~ 'xlopok'
            continue
        score = int(fuzz.ratio(tok, alias))
        if len(alias) <= 6 and score < 90:
            score = 0  # short aliases: only near-exact ('izvest' must not match 'invest')
        best = max(best, score)
    return best


def resolve_products(question: str) -> list[ProductHit]:
    tokens = translit(question).split()
    if not tokens:
        return []
    ngrams = {n: [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)] for n in (2, 3, 4)}
    best: dict[str, tuple[int, str]] = {}
    for alias, tnved in _PRODUCT_INDEX:
        score = _alias_score(alias, tokens, ngrams)
        if score < PRODUCT_MIN_SCORE:
            continue
        prev = best.get(tnved)
        if prev is None or (score, len(alias)) > (prev[0], len(prev[1])):
            best[tnved] = (score, alias)
    ranked = sorted(best.items(), key=lambda kv: (-kv[1][0], -len(kv[1][1]), kv[0]))
    return [ProductHit(tnved=t, name_ru=PRODUCTS[t][0], name_uz=PRODUCTS[t][1], score=s, matched=a)
            for t, (s, a) in ranked[:MAX_PRODUCT_HITS]]


# ----------------------------------------------------------------------------- phrases
def _is_capitalised(word: str) -> bool:
    return word[0].isupper()


def _clean_phrase_words(words: list[str]) -> str:
    """Drop legal forms, regions and stop words; return the remaining phrase (original casing)."""
    kept = [w for w in words
            if translit(w) and translit(w) not in _STOP_WORDS and translit(w) not in _REGION_WORDS
            and w.lower() not in _LEGAL_FORMS_RAW]
    return " ".join(kept)


def extract_phrases(question: str) -> list[str]:
    """Candidate company/broker name phrases: quoted strings, runs of capitalised words,
    words before a legal form (MCHJ/OOO/...) or before 'broker'."""
    phrases: list[str] = []
    stripped = _BROKER_CODE_RE.sub(" ", question)
    for m in _QUOTED_RE.finditer(question):
        phrases.append((m.group(1) or m.group(2)).strip())
        stripped = stripped.replace(m.group(0), " ")
    words = [(m.group(0), m.start()) for m in _WORD_RE.finditer(stripped)]
    run: list[str] = []
    for idx, (word, _) in enumerate(words):
        if _is_capitalised(word) or (run and word.lower() in _LEGAL_FORMS_RAW):
            run.append(word)
            continue
        if word.lower() in _LEGAL_FORMS_RAW and not run:
            run = [w for w, _ in words[max(0, idx - 3):idx]] + [word]
        _flush_run(run, phrases, first=idx - len(run) == 0)
        run = []
    _flush_run(run, phrases, first=len(words) - len(run) == 0)
    for m in _BROKER_WORD_RE.finditer(stripped):
        phrases.append(m.group(1))
    out: list[str] = []
    for p in phrases:
        cleaned = _clean_phrase_words(p.split())
        if len(company_key(cleaned)) >= 4 and cleaned not in out:
            out.append(cleaned)
    return out[:MAX_PHRASES]


def _flush_run(run: list[str], phrases: list[str], first: bool) -> None:
    if not run:
        return
    has_form = any(w.lower() in _LEGAL_FORMS_RAW for w in run)
    if first and len(run) == 1 and not has_form:
        return  # a lone capitalised first word is just the sentence start
    phrases.append(" ".join(run))


# ----------------------------------------------------------------------------- resolver
class EntityResolver:
    def __init__(self, con: sqlite3.Connection) -> None:
        rows = con.execute("SELECT inn, name, name_key, region FROM participants").fetchall()
        self._participants = {inn: (name, region) for inn, name, _, region in rows}
        self._key_to_inns: dict[str, list[str]] = {}
        for inn, _, key, _ in rows:
            self._key_to_inns.setdefault(key or "", []).append(inn)
        self._keys = [k for k in self._key_to_inns if k]
        brokers = con.execute("SELECT code, name, name_key FROM brokers").fetchall()
        self._broker_keys = {key: code for code, _, key in brokers if key}
        self._broker_codes = {code for code, _, _ in brokers}

    # -- public
    def resolve(self, question: str) -> Resolution:
        inns = _unique(_INN_RE.findall(question))
        deal_nos = _unique(int(n) for n in _LONG_NUMBER_RE.findall(question) if len(n) != 9)
        brokers = _unique(f"BK{m}" for m in _BROKER_CODE_RE.findall(question))
        phrases = extract_phrases(question)
        companies: list[CompanyHit] = []
        unmatched: list[str] = []
        for phrase in phrases:
            key = company_key(phrase)
            broker = self._match_broker(key)
            if broker:
                brokers.append(broker)
                continue
            hits = self._match_companies(key)
            if hits:
                companies.extend(h for h in hits if h.inn not in {c.inn for c in companies})
            else:
                unmatched.append(phrase)
        companies.sort(key=lambda c: (-c.score, c.inn))
        return Resolution(products=resolve_products(question), companies=companies, brokers=_unique(brokers),
                          inns=inns, deal_nos=deal_nos, unmatched_phrases=unmatched)

    # -- private
    def _match_broker(self, key: str) -> str | None:
        hit = process.extractOne(key, list(self._broker_keys), scorer=fuzz.WRatio, score_cutoff=BROKER_CUTOFF)
        return self._broker_keys[hit[0]] if hit else None

    def _match_companies(self, key: str) -> list[CompanyHit]:
        scores: dict[str, int] = {}
        substr = [k for k in self._keys if key in k]
        if len(substr) <= MAX_SUBSTRING_HITS:
            for k in substr:
                scores[k] = 100
        for k, score, _ in process.extract(key, self._keys, scorer=fuzz.WRatio, limit=COMPANY_LIMIT,
                                           score_cutoff=COMPANY_CUTOFF):
            scores.setdefault(k, int(score))
        if 100 in scores.values():
            scores = {k: s for k, s in scores.items() if s >= 95}  # exact hits present: drop fuzzy noise
        hits = [CompanyHit(inn=inn, name=self._participants[inn][0], region=self._participants[inn][1], score=s)
                for k, s in scores.items() for inn in self._key_to_inns[k]]
        hits.sort(key=lambda h: (-h.score, h.inn))
        return hits[:COMPANY_LIMIT * 2]


def _unique(items) -> list:
    out: list = []
    for it in items:
        if it not in out:
            out.append(it)
    return out
