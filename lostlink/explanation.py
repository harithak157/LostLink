from __future__ import annotations
from typing import List

from .inference import InferenceEngine, WorkingMemory


def _indent(lines: List[str], prefix: str = "    ") -> List[str]:
    return [prefix + l for l in lines]


class ExplanationFacility:
    def __init__(self, engine: InferenceEngine):
        self.engine = engine
        self.wm: WorkingMemory = engine.wm

    # --------------------------------------------------------------- how
    def how(self, fact: str) -> str:
        """Full proof tree for a fact."""
        if not self.wm.has(fact):
            return self._why_not(fact)
        return "\n".join(self._proof(fact, depth=0))

    def _proof(self, fact: str, depth: int) -> List[str]:
        just = self.wm.justification(fact)
        pad = "  " * depth
        if just is None:
            return [f"{pad}? {fact}  (unknown)"]
        if just.is_given:
            return [f"{pad}* {fact}  [given]"]
        lines = [f"{pad}+ {fact}"]
        lines.append(f"{pad}  because rule {just.rule_id} fired")
        for ant in just.antecedents:
            if ant.startswith("signal:"):
                lines.append(f"{pad}    - {ant[len('signal:'):]}")
            elif self.wm.has(ant):
                lines.extend(self._proof(ant, depth + 2))
            else:
                lines.append(f"{pad}    - {ant}  [not in WM]")
        return lines

    # --------------------------------------------------------------- why
    def why(self, fact: str) -> str:
        """One-step justification for a fact."""
        just = self.wm.justification(fact)
        if just is None:
            return f"'{fact}' is not in working memory."
        if just.is_given:
            return f"'{fact}' is a given/base fact."
        return (f"'{fact}' was derived by rule {just.rule_id}.\n"
                f"  Antecedents:\n" + "\n".join(f"    - {a}" for a in just.antecedents))

    # --------------------------------------------------------- why_not
    def why_not(self, fact: str) -> str:
        if self.wm.has(fact):
            return f"'{fact}' IS in working memory; why_not is not applicable."
        # Find rules whose derived fact could structurally match
        head = fact.split("(", 1)[0] + "("
        lines = [f"'{fact}' could not be derived. Reasons:"]
        for r in self.engine.rules:
            # Probe each context to see what was missing
            for ctx in self.engine.contexts:
                produced = r.when(ctx)
                if produced and produced.split("(", 1)[0] + "(" == head:
                    lines.append(f"  - rule {r.id} ({r.name}) was eligible on a context "
                                 f"but the fact was not asserted")
        if len(lines) == 1:
            lines.append("  - no rule can produce this predicate with the current signals")
        return "\n".join(lines)

    # ----------------------------------------------------------- report
    def trace_report(self) -> str:
        out = [f"{'step':>4}  {'rule':<5} {'conflicts':>9}  fact"]
        for f in self.engine.trace:
            out.append(f"{f.step:>4}  {f.rule_id:<5} {f.conflicts:>9}  {f.fact}")
        return "\n".join(out)

    def facts_report(self) -> str:
        out = []
        for fact in sorted(self.wm.facts()):
            j = self.wm.justification(fact)
            tag = "given" if j.is_given else j.rule_id
            out.append(f"[{tag:>5}] {fact}")
        return "\n".join(out)
    def natural_language_explanation(self, fact: str) -> str:
            """Translate the technical proof tree into plain English."""
            just = self.wm.justification(fact)
            if not just or just.is_given:
                return "These items match based on the initial data provided."
    
            lines = ["The AI system flagged this as a potential match because:"]
            
            for ant in just.antecedents:
                if ant.startswith("text_strong"):
                    lines.append("• The item descriptions and names are highly similar.")
                elif ant.startswith("time_close"):
                    lines.append("• They were reported within a similar time frame (within 48 hours).")
                elif ant.startswith("loc_close"):
                    lines.append("• They were lost and found in the same or a nearby campus location.")
                elif ant.startswith("cat_match"):
                    lines.append("• They belong to the exact same category.")
                elif ant.startswith("img_similar"):
                    lines.append("• The uploaded photos share visual similarities.")
                elif ant.startswith("signal:"):
                    lines.append(f"• {ant[7:]}")
                else:
                    clean = ant.split('(')[0].replace('_', ' ').capitalize()
                    lines.append(f"• {clean}.")
            
            return "\n".join(lines)