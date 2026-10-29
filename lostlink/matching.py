from __future__ import annotations
import math
from typing import List

from .models import Item, PairContext
from .nlp import text_similarity
from .image_sim import histogram_similarity

LOC_GROUPS = [0, 0, 0, 1, 2, 1, 2, 0]   # same grouping as the HTML


def location_similarity(a: Item, b: Item) -> float:
    if a.location_index == b.location_index:
        return 1.0
    if LOC_GROUPS[a.location_index] == LOC_GROUPS[b.location_index]:
        return 0.55
    return 0.15


def time_similarity(lost: Item, found: Item) -> float:
    hours = abs(found.timestamp - lost.timestamp) / 3600.0
    if lost.timestamp > found.timestamp + 2 * 3600:
        # found BEFORE lost by more than 2h → unlikely
        return 0.1
    return math.exp(-hours / 48.0)


def build_pair(lost: Item, found: Item) -> PairContext:
    cat_same = lost.category.lower() == found.category.lower()
    txt = text_similarity(
        (lost.name, lost.category, lost.description),
        (found.name, found.category, found.description),
    )
    loc = location_similarity(lost, found)
    tim = time_similarity(lost, found)
    img = histogram_similarity(lost.histogram, found.histogram)
    return PairContext(lost, found, cat_same, txt, loc, tim, img)


def build_all_pairs(lost_items: List[Item], found_items: List[Item]) -> List[PairContext]:
    return [build_pair(l, f) for l in lost_items for f in found_items
            if l.id != f.id and f.status not in ("returned",)]