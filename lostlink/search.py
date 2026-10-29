from __future__ import annotations
import heapq, time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

Candidate = Tuple[str, float]           # (found_id, score)
CandidateMap = Dict[str, List[Candidate]]


@dataclass
class SearchResult:
    algorithm: str
    weight: float
    found: bool
    pairs: List[Tuple[str, str]]
    cost: float                          # total match score (positive)
    expanded: int = 0
    generated: int = 0
    frontier_peak: int = 0
    expansion_order: List[str] = field(default_factory=list)
    elapsed_ms: float = 0.0


def _prune(cands: CandidateMap, threshold: float) -> CandidateMap:
    return {k: [c for c in v if c[1] >= threshold]
            for k, v in cands.items() if any(c[1] >= threshold for c in v)}


def _bound_remaining(remaining_lost: Tuple[str, ...],
                     remaining_found: frozenset,
                     cands: CandidateMap) -> float:
    """Admissible heuristic: upper bound = sum of best reachable scores."""
    total = 0.0
    for l in remaining_lost:
        best = 0.0
        for f, s in cands.get(l, ()):
            if f in remaining_found and s > best:
                best = s
        total += best
    return total


def best_first_assignment(cands: CandidateMap, weight: float = 1.0,
                          max_nodes: int = 20000) -> SearchResult:
    """A* over assignments. cost = -sum(scores); heuristic = -upper-bound."""
    cands = _prune(cands, threshold=0.0)
    lost = tuple(sorted(cands.keys()))
    found = frozenset({f for v in cands.values() for f, _ in v})

    if not lost:
        return SearchResult("astar", weight, True, [], 0.0)

    start = ((-0.0, 0.0), (), lost, found, ())  # placeholder for heapq
    # We'll use a proper priority queue with (f, tiebreak, g, state)
    counter = 0
    start_state = ((), lost, found)              # (pairs, remaining_lost, remaining_found)
    start_g = 0.0
    start_h = -_bound_remaining(lost, found, cands)
    heap: List[Tuple[float, int, float, tuple]] = [
        (start_g + weight * start_h, counter, start_g, start_state)
    ]
    best_goal = None
    best_goal_g = 0.0
    expanded = 0
    generated = 1
    peak = 1
    order: List[str] = []

    while heap and expanded < max_nodes:
        f, _, g, state = heapq.heappop(heap)
        pairs, remaining_lost, remaining_found = state
        expanded += 1
        order.append(f"L{len(pairs)}:g={-g:.2f}")

        if not remaining_lost:
            best_goal, best_goal_g = pairs, g
            break

        # Expand the first remaining lost
        l = remaining_lost[0]
        rest_lost = remaining_lost[1:]
        for f_id, s in cands.get(l, ()):
            if f_id not in remaining_found:
                continue
            new_pairs = pairs + ((l, f_id),)
            new_found = remaining_found - {f_id}
            new_g = g - s
            h = -_bound_remaining(rest_lost, new_found, cands)
            new_f = new_g + weight * h
            generated += 1
            heapq.heappush(heap, (new_f, generated, new_g,
                                  (new_pairs, rest_lost, new_found)))
        peak = max(peak, len(heap))

    if best_goal is None:
        return SearchResult("astar", weight, False, [], 0.0,
                            expanded, generated, peak, order)

    return SearchResult(
        algorithm="astar", weight=weight, found=True,
        pairs=list(best_goal), cost=-best_goal_g,
        expanded=expanded, generated=generated,
        frontier_peak=peak, expansion_order=order,
    )


def greedy_assignment(cands: CandidateMap) -> SearchResult:
    """Baseline: sort all pairs by score desc, greedily accept non-conflicting."""
    pairs_all = sorted(
        ((l, f, s) for l, v in cands.items() for f, s in v),
        key=lambda t: (-t[2], t[0], t[1]),
    )
    used_lost, used_found, chosen = set(), set(), []
    for l, f, s in pairs_all:
        if l in used_lost or f in used_found:
            continue
        used_lost.add(l)
        used_found.add(f)
        chosen.append((l, f))
    total = sum(dict((l, {f: s for f, s in v})[f])[f] if False else
                next(s for l2, f2, s in pairs_all if l2 == l and f2 == f)
                for l, f in chosen)
    return SearchResult("greedy", 1.0, True, chosen, total,
                        expanded=len(pairs_all), generated=len(pairs_all),
                        frontier_peak=0)