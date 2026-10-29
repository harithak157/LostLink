from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .models import PairContext
from .rules import Rule, build_rules


@dataclass
class Justification:
    fact: str
    rule_id: Optional[str]          # None = base / given fact
    antecedents: List[str] = field(default_factory=list)

    @property
    def is_given(self) -> bool:
        return self.rule_id is None


@dataclass
class Firing:
    step: int
    rule_id: str
    fact: str
    conflicts: int                  # other rules eligible this round
    antecedents: List[str]


@dataclass
class FailedAttempt:
    rule_id: str
    context_key: str
    reason: str                     # short human text


class WorkingMemory:
    def __init__(self) -> None:
        self._just: Dict[str, Justification] = {}

    def add(self, fact: str, just: Justification) -> bool:
        if fact in self._just:
            return False
        self._just[fact] = just
        return True

    def has(self, fact: str) -> bool:
        return fact in self._just

    def facts(self) -> List[str]:
        return list(self._just.keys())

    def justification(self, fact: str) -> Optional[Justification]:
        return self._just.get(fact)

    def __len__(self) -> int:
        return len(self._just)


class InferenceEngine:
    """Forward chaining over PairContexts."""

    def __init__(self, contexts: List[PairContext], rules: Optional[List[Rule]] = None):
        self.contexts = contexts
        self.rules = rules or build_rules()
        self.wm = WorkingMemory()
        self.trace: List[Firing] = []
        self.failures: List[FailedAttempt] = []

    def run(self, max_steps: int = 2000) -> None:
        for step in range(max_steps):
            # 1. Gather all (rule, ctx) pairs whose condition fires this round.
            eligible: List[tuple] = []
            for ctx in self.contexts:
                key = f"{ctx.lost.id}|{ctx.found.id}"
                for rule in self.rules:
                    fact = rule.when(ctx)
                    if fact and not self.wm.has(fact):
                        eligible.append((rule, ctx, fact, key))

            if not eligible:
                return

            # 2. Conflict resolution: highest priority first, then stable by context.
            eligible.sort(key=lambda e: (-e[0].priority, e[3], e[0].id))
            rule, ctx, fact, key = eligible[0]
            antecedents = self._antecedents_of(rule, ctx)
            just = Justification(fact=fact, rule_id=rule.id, antecedents=antecedents)
            if self.wm.add(fact, just):
                self.trace.append(Firing(
                    step=len(self.trace) + 1,
                    rule_id=rule.id,
                    fact=fact,
                    conflicts=len(eligible) - 1,
                    antecedents=antecedents,
                ))

            # 3. Record all non-winning eligible rules as "deferred" (nothing to do).
            # 4. Also record failures for rules that COULD have fired on this context
            #    but did not, to support why_not.
            for r in self.rules:
                if r is rule:
                    continue
                for c in self.contexts:
                    target = r.when(c)
                    if target and not self.wm.has(target):
                        self.failures.append(FailedAttempt(
                            rule_id=r.id,
                            context_key=f"{c.lost.id}|{c.found.id}",
                            reason="won by higher-priority rule",
                        ))

    def _antecedents_of(self, rule: Rule, ctx: PairContext) -> List[str]:
        """Explain which signals supported this derivation."""
        out: List[str] = []
        if rule.id in {"R1", "R2", "R3", "R4", "R5"}:
            out.append(f"signal:{rule.name}")
        elif rule.id == "R6":
            out += [f"cat_match({ctx.lost.id},{ctx.found.id})"
                    if ctx.cat_same else "",
                    f"text_strong({ctx.lost.id},{ctx.found.id})"
                    if ctx.text_sim >= 0.5 else "",
                    f"loc_close({ctx.lost.id},{ctx.found.id})"
                    if ctx.loc_sim >= 0.5 else ""]
        elif rule.id in {"R7", "R9"}:
            out += [f"text_strong({ctx.lost.id},{ctx.found.id})"
                    if ctx.text_sim >= 0.5 else "",
                    f"time_close({ctx.lost.id},{ctx.found.id})"
                    if ctx.time_sim >= 0.5 else "",
                    f"loc_close({ctx.lost.id},{ctx.found.id})"
                    if ctx.loc_sim >= 0.5 else ""]
        elif rule.id in {"R8", "R11"}:
            out += [f"img_similar({ctx.lost.id},{ctx.found.id})"
                    if ctx.img_sim is not None and ctx.img_sim >= 0.5 else "",
                    f"cat_match({ctx.lost.id},{ctx.found.id})"
                    if ctx.cat_same else ""]
        elif rule.id == "R10":
            out += ["found.secret != empty",
                    f"cat_match({ctx.lost.id},{ctx.found.id})"]
        return [a for a in out if a]