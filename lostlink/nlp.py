from __future__ import annotations
import math
from typing import Dict, List

SYNONYMS = {
    "earbuds": "earphones", "airpods": "earphones", "headphones": "earphones",
    "headphone": "earphones", "earphone": "earphones",
    "flask": "bottle", "purse": "wallet", "mobile": "phone",
    "smartphone": "phone", "laptop": "computer", "backpack": "bag",
    "identity": "id", "idcard": "id", "card": "id", "notebook": "book",
    "textbook": "book", "books": "book", "key": "keys", "keychain": "keys",
}
STOP = set("a an the of in on at is it my its with and or to for was has "
           "have this that very some from by".split())


def _stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def tokenize(text: str) -> List[str]:
    out, seen = [], set()
    for raw in (text or "").lower().split():
        w = "".join(c for c in raw if c.isalnum())
        if not w or w in STOP:
            continue
        w = SYNONYMS.get(w, _stem(w))
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out


def cosine(tokens_a: List[str], tokens_b: List[str]) -> float:
    if not tokens_a or not tokens_b:
        return 0.0
    sa, sb = set(tokens_a), set(tokens_b)
    return len(sa & sb) / math.sqrt(len(sa) * len(sb))


def item_tokens(name: str, category: str, description: str) -> List[str]:
    return tokenize(f"{name} {category} {description}")


def text_similarity(a: tuple, b: tuple) -> float:
    """a, b are (name, category, description) triples."""
    ta = item_tokens(*a)
    tb = item_tokens(*b)
    base = cosine(ta, tb)
    if a[1].lower() == b[1].lower():
        base = min(1.0, base + 0.15)
    return base