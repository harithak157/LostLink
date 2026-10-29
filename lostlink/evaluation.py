from __future__ import annotations
import random, statistics, time
from typing import Dict, List, Tuple

from .models import Item
from .matching import build_pair
from .search import best_first_assignment, greedy_assignment, SearchResult


def _candidates_for(lost: Item, found: List[Item], threshold: float = 0.0):
    out = {}
    for f in found:
        if f.status == "returned":
            continue
        ctx = build_pair(lost, f)
        out[f.id] = (f, ctx.score())
    return out


def _candidates_map(lost_items: List[Item], found_items: List[Item]):
    cm = {}
    for l in lost_items:
        for f in found_items:
            if f.status == "returned":
                continue
            s = build_pair(l, f).score()
            cm.setdefault(l.id, []).append((f.id, s))
    return cm


def _hit_at(pairs: List[Tuple[str, str]], truth: Dict[str, str], k: int) -> float:
    if not truth:
        return 0.0
    hits = 0
    for l, f in pairs[:k]:
        if truth.get(l) == f:
            hits += 1
    return hits / min(k, len(truth))


def _mrr(pairs: List[Tuple[str, str]], truth: Dict[str, str]) -> float:
    rr = []
    for l, target in truth.items():
        for rank, (l2, f) in enumerate(pairs):
            if l2 == l:
                if f == target:
                    rr.append(1.0 / (rank + 1))
                break
        else:
            rr.append(0.0)
    return sum(rr) / len(rr) if rr else 0.0


def benchmark(lost_items: List[Item], found_items: List[Item],
              truth: Dict[str, str], trials: int = 20,
              seed: int = 7, verbose: bool = False) -> str:
    rng = random.Random(seed)
    heuristic_runs: List[SearchResult] = []
    baseline_runs: List[SearchResult] = []
    h_metrics = {"p@1": [], "p@3": [], "mrr": []}
    b_metrics = {"p@1": [], "p@3": [], "mrr": []}

    for _ in range(trials):
        subset = list(lost_items)
        rng.shuffle(subset)
        subset = subset[:max(1, len(subset) // 2 + 1)]
        cm = _candidates_map(subset, found_items)

        t0 = time.perf_counter()
        h = best_first_assignment(cm, weight=1.0, max_nodes=5000)
        h.elapsed_ms = (time.perf_counter() - t0) * 1000
        heuristic_runs.append(h)

        t0 = time.perf_counter()
        b = greedy_assignment(cm)
        b.elapsed_ms = (time.perf_counter() - t0) * 1000
        baseline_runs.append(b)

        for name, res, metrics in [
            ("heuristic", h, h_metrics),
            ("baseline", b, b_metrics),
        ]:
            metrics["p@1"].append(_hit_at(res.pairs, truth, 1))
            metrics["p@3"].append(_hit_at(res.pairs, truth, 3))
            metrics["mrr"].append(_mrr(res.pairs, truth))

    def agg(xs):
        return statistics.mean(xs) if xs else 0.0

    lines = []
    lines.append("EVALUATION: baseline (greedy text+signals) vs heuristic (A* assignment)")
    lines.append(f"  trials                          : {trials}")
    lines.append(f"  open lost items                 : {len(lost_items)}")
    lines.append(f"  open found items                : {len(found_items)}")
    lines.append("")
    lines.append(f"  {'metric':<24}{'baseline':>14}{'heuristic':>14}")
    lines.append(f"  {'-'*24}{'-'*14:>14}{'-'*14:>14}")
    lines.append(f"  {'precision@1':<24}{agg(b_metrics['p@1']):>14.3f}{agg(h_metrics['p@1']):>14.3f}")
    lines.append(f"  {'precision@3':<24}{agg(b_metrics['p@3']):>14.3f}{agg(h_metrics['p@3']):>14.3f}")
    lines.append(f"  {'mean reciprocal rank':<24}{agg(b_metrics['mrr']):>14.3f}{agg(h_metrics['mrr']):>14.3f}")
    lines.append(f"  {'avg expansions':<24}"
                 f"{agg([r.expanded for r in baseline_runs]):>14.1f}"
                 f"{agg([r.expanded for r in heuristic_runs]):>14.1f}")
    lines.append(f"  {'avg runtime (ms)':<24}"
                 f"{agg([r.elapsed_ms for r in baseline_runs]):>14.2f}"
                 f"{agg([r.elapsed_ms for r in heuristic_runs]):>14.2f}")
    lines.append(f"  {'avg total score':<24}"
                 f"{agg([r.cost for r in baseline_runs]):>14.2f}"
                 f"{agg([r.cost for r in heuristic_runs]):>14.2f}")
    if verbose:
        lines.append("")
        lines.append("  sample heuristic expansion (first trial):")
        for s in heuristic_runs[0].expansion_order[:20]:
            lines.append(f"    {s}")
    return "\n".join(lines)