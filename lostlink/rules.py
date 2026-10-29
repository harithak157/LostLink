from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List

from .models import PairContext


@dataclass
class Rule:
    id: str
    name: str
    priority: int
    # Given a context, return the fact string to derive, or None if not applicable.
    when: Callable[[PairContext], "str | None"]


# Base facts emitted directly from signals (priority 100 = highest)
def _r_base_cat(ctx: PairContext):
    return f"cat_match({ctx.lost.id},{ctx.found.id})" if ctx.cat_same else None


def _r_base_text(ctx: PairContext):
    return f"text_strong({ctx.lost.id},{ctx.found.id})" if ctx.text_sim >= 0.5 else None


def _r_base_loc(ctx: PairContext):
    return f"loc_close({ctx.lost.id},{ctx.found.id})" if ctx.loc_sim >= 0.5 else None


def _r_base_time(ctx: PairContext):
    return f"time_close({ctx.lost.id},{ctx.found.id})" if ctx.time_sim >= 0.5 else None


def _r_base_img(ctx: PairContext):
    if ctx.img_sim is not None and ctx.img_sim >= 0.5:
        return f"img_similar({ctx.lost.id},{ctx.found.id})"
    return None


# Derived facts
def _r_context_consistent(ctx: PairContext):
    l, f = ctx.lost.id, ctx.found.id
    if (ctx.cat_same and ctx.text_sim >= 0.5 and ctx.loc_sim >= 0.5):
        return f"context_consistent({l},{f})"
    return None


def _r_likely(ctx: PairContext):
    l, f = ctx.lost.id, ctx.found.id
    if ctx.cat_same and ctx.text_sim >= 0.5 and ctx.time_sim >= 0.5:
        return f"likely_match({l},{f})"
    return None


def _r_high_conf(ctx: PairContext):
    l, f = ctx.lost.id, ctx.found.id
    if (ctx.img_sim is not None and ctx.img_sim >= 0.55
            and ctx.cat_same and ctx.text_sim >= 0.5):
        return f"high_conf_match({l},{f})"
    return None


def _r_candidate(ctx: PairContext):
    l, f = ctx.lost.id, ctx.found.id
    # Fires if a supporting derived fact could have fired
    if (ctx.cat_same and ctx.text_sim >= 0.5
            and (ctx.time_sim >= 0.5 or ctx.loc_sim >= 0.5)):
        return f"match_candidate({l},{f})"
    return None


def _r_requires_verification(ctx: PairContext):
    l, f = ctx.lost.id, ctx.found.id
    if ctx.found.secret and ctx.cat_same and ctx.text_sim >= 0.5:
        return f"requires_verification({l},{f})"
    return None


def _r_auto_notify(ctx: PairContext):
    l, f = ctx.lost.id, ctx.found.id
    if (ctx.img_sim is not None and ctx.img_sim >= 0.55
            and ctx.cat_same and ctx.text_sim >= 0.55):
        return f"auto_notify({l},{f})"
    return None


def build_rules() -> List[Rule]:
    return [
        Rule("R1", "Category match",               100, _r_base_cat),
        Rule("R2", "Strong text similarity",       100, _r_base_text),
        Rule("R3", "Locations in same zone",       100, _r_base_loc),
        Rule("R4", "Time proximity (48h window)",  100, _r_base_time),
        Rule("R5", "Image histogram similar",      100, _r_base_img),
        Rule("R6", "Text + location consistent",    70, _r_context_consistent),
        Rule("R7", "Category + text + time",        60, _r_likely),
        Rule("R8", "High-confidence (with image)",  50, _r_high_conf),
        Rule("R9", "Candidate for review",          40, _r_candidate),
        Rule("R10","Owner verification required",   30, _r_requires_verification),
        Rule("R11","Auto-notify potential owner",   20, _r_auto_notify),
    ]