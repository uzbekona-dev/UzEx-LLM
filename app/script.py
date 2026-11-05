"""Uzbek script mirroring: a question written in Uzbek Cyrillic gets its answer in Uzbek Cyrillic.

The answer is always produced in Uzbek Latin (what the prompts and tests are tuned for) and converted
here, deterministically. Only our own wording is converted: {slots}, numbers, codes (BK045) and
upper-case acronyms (SQL, UZS, DAP) are left alone; data values (company names) are filled in after
conversion, so they stay exactly as in the database.
"""

from __future__ import annotations

import re

UZ_CYR = "uz_cyr"

_APOS = "'‘’ʻʼ`"
_DIGRAPHS = {
    "o'": "ў", "g'": "ғ", "sh": "ш", "ch": "ч", "yo": "ё", "yu": "ю", "ya": "я", "ye": "е",
}
_SINGLE = {
    "a": "а", "b": "б", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "ҳ", "i": "и", "j": "ж", "k": "к",
    "l": "л", "m": "м", "n": "н", "o": "о", "p": "п", "q": "қ", "r": "р", "s": "с", "t": "т", "u": "у",
    "v": "в", "x": "х", "y": "й", "z": "з", "c": "с", "w": "в",
}
_UPPER_KEEP = {"STIR": "СТИР", "QQS": "ҚҚС"}  # acronyms that do have a Cyrillic form
_TOKEN_RE = re.compile(r"\{[^{}]*\}|[^\W\d_][\w'‘’ʻʼ`-]*|.", re.S)


def is_cyrillic(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and sum("Ѐ" <= c <= "ӿ" for c in letters) / len(letters) > 0.5


def _word_to_cyr(word: str) -> str:
    if any(ch.isdigit() for ch in word):
        return word  # codes like BK045, 2024-yil handled by the caller splitting on digits
    if word.isupper() and len(word) >= 2:
        return _UPPER_KEEP.get(word, word)  # SQL, UZS, DAP, TN, VED ...
    if not any("a" <= ch.lower() <= "z" for ch in word):
        return word  # already Cyrillic or punctuation
    out: list[str] = []
    i = 0
    norm = word
    for ap in _APOS[1:]:
        norm = norm.replace(ap, "'")
    while i < len(norm):
        ch = norm[i]
        low = ch.lower()
        pair = norm[i:i + 2].lower()
        if pair in ("yo", "yu", "ya", "ye") and norm[i + 2:i + 3] == "'":
            pair = ""  # yo'q -> й + ў + қ, not ё + ъ
        if pair in _DIGRAPHS:
            cyr = _DIGRAPHS[pair]
            out.append(cyr.upper() if ch.isupper() else cyr)
            i += 2
            continue
        if low == "'":
            out.append("ъ")  # tutuq belgisi (ma'lumot -> маълумот)
        elif low == "e" and i == 0:
            out.append("Э" if ch.isupper() else "э")
        elif low in _SINGLE:
            cyr = _SINGLE[low]
            out.append(cyr.upper() if ch.isupper() else cyr)
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def lat_to_cyr(text: str) -> str:
    """Uzbek Latin -> Uzbek Cyrillic for our own text; {slots}, digits and acronyms are preserved."""
    parts: list[str] = []
    for m in _TOKEN_RE.finditer(text):
        tok = m.group(0)
        if tok.startswith("{") and tok.endswith("}"):
            parts.append(tok)
        elif tok[:1].isalpha():
            parts.append(_word_to_cyr(tok))
        else:
            parts.append(tok)
    return "".join(parts)


def base_lang(lang: str) -> str:
    """'uz_cyr' behaves like 'uz' everywhere except the final script."""
    return "uz" if lang == UZ_CYR else lang
