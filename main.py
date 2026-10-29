from __future__ import annotations
import argparse, subprocess, sys

from lostlink.store import Store
from lostlink.matching import build_pair
from lostlink.inference import InferenceEngine
from lostlink.explanation import ExplanationFacility
from lostlink.search import best_first_assignment, greedy_assignment
from lostlink.evaluation import benchmark

W = 78


def hr(title=""):
    print("\n" + "=" * W)
    if title:
        print(title)
        print("=" * W)


def section(title):
    print("\n" + "-" * W)
    print(title)
    print("-" * W)


def _candidates(lost, found):
    return [(f, build_pair(lost, f)) for f in found if f.status != "returned" and f.id != lost.id]


def cmd_demo(args):
    store = Store()
    items = store.list_items()
    lost = [i for i in items if i.type == "lost" and i.status == "open"]
    found = [i for i in items if i.type == "found" and i.status == "open"]

    hr("LostLink AI demonstration")
    print(f"  open lost items  : {len(lost)}")
    print(f"  open found items : {len(found)}")

    if not lost:
        print("No open lost items — try 'python main.py reset'.")
        return

    for l in lost:
        section(f"Lost item: {l.name} ({l.reported_by})")
        contexts = [build_pair(l, f) for f in found if f.status != "returned" and f.id != l.id]
        engine = InferenceEngine(contexts)
        engine.run()
        expl = ExplanationFacility(engine)

        print(f"  pair contexts: {len(contexts)}")
        print(f"  rules fired  : {len(engine.trace)}")
        for f in engine.trace[:8]:
            print(f"    step {f.step:>2}  {f.rule_id:<4} conf={f.conflicts:<2}  {f.fact}")
        if len(engine.trace) > 8:
            print(f"    ... ({len(engine.trace) - 8} more)")

        candidates = {}
        for c in contexts:
            if engine.wm.has(f"match_candidate({l.id},{c.found.id})") \
                    or engine.wm.has(f"likely_match({l.id},{c.found.id})") \
                    or engine.wm.has(f"high_conf_match({l.id},{c.found.id})"):
                candidates.setdefault(l.id, []).append((c.found.id, c.score()))

        if not candidates:
            print("  no candidates — nothing to search")
            continue

        g = greedy_assignment(candidates)
        a = best_first_assignment(candidates, weight=1.0)
        print(f"\n  baseline greedy  : pairs={g.pairs} score={g.cost:.2f} expansions={g.expanded}")
        print(f"  heuristic A*     : pairs={a.pairs} score={a.cost:.2f} expansions={a.expanded}")

        top = max(contexts, key=lambda c: c.score())
        target = f"likely_match({l.id},{top.found.id})"
        if not engine.wm.has(target):
            target = f"match_candidate({l.id},{top.found.id})"
        print("\n  HOW was a match derived?")
        print(expl(engine) if False else expl.how(target))

    hr("Benchmark")
    print(benchmark(lost, found,
                    {l.id: max([c.found.id for c in [build_pair(l, f) for f in found
                                if f.status != "returned" and f.id != l.id]],
                               key=lambda fid: max(
                                   (build_pair(l, f).score() for f in found if f.id == fid),
                                   default=0))
                     for l in lost},
                    trials=20, seed=7))


def cmd_serve(args):
    from server import main as run
    run(host=args.host, port=args.port)


def cmd_bench(args):
    store = Store()
    items = store.list_items()
    lost = [i for i in items if i.type == "lost" and i.status == "open"]
    found = [i for i in items if i.type == "found" and i.status == "open"]
    if not lost or not found:
        print("Not enough items to benchmark. Try 'python main.py reset'.")
        return
    truth = {}
    for l in lost:
        best, bs = None, 0.0
        for f in found:
            s = build_pair(l, f).score()
            if s > bs:
                best, bs = f.id, s
        if best:
            truth[l.id] = best
    hr("BENCHMARK")
    print(benchmark(lost, found, truth, trials=args.trials, seed=args.seed, verbose=args.verbose))


def cmd_explain(args):
    store = Store()
    l = store.get_item(args.lost)
    f = store.get_item(args.found)
    if not l or not f:
        print("Item not found.")
        return
    ctx = build_pair(l, f)
    engine = InferenceEngine([ctx])
    engine.run()
    expl = ExplanationFacility(engine)

    hr(f"EXPLAIN {l.name} ↔ {f.name}")
    print(f"signals: text={ctx.text_sim:.2f}  loc={ctx.loc_sim:.2f}  "
          f"time={ctx.time_sim:.2f}  img={ctx.img_sim if ctx.img_sim is None else round(ctx.img_sim, 2)}")
    print(f"combined score: {ctx.score():.3f}")

    for pred in ("high_conf_match", "likely_match", "match_candidate"):
        fact = f"{pred}({l.id},{f.id})"
        if engine.wm.has(fact):
            section(f"HOW: {fact}")
            print(expl.how(fact))
            section(f"WHY: {fact}")
            print(expl.why(fact))
        else:
            section(f"WHY NOT: {fact}")
            print(expl.why_not(fact))
    section("Full inference trace")
    print(expl.trace_report())


def cmd_reset(args):
    Store().reset()
    print("Reset to seed data.")


def cmd_test(args):
    return subprocess.call([sys.executable, "-m", "unittest", "discover",
                            "-s", "tests", "-t", ".", "-v"])


def main(argv=None):
    p = argparse.ArgumentParser(description="LostLink AI backend")
    sp = p.add_subparsers(dest="cmd")

    a = sp.add_parser("demo", help="run the full AI demo")
    a.set_defaults(func=cmd_demo)

    a = sp.add_parser("serve", help="start HTTP server")
    a.add_argument("--host", default="127.0.0.1")
    a.add_argument("--port", type=int, default=8000)
    a.set_defaults(func=cmd_serve)

    a = sp.add_parser("bench", help="run benchmark")
    a.add_argument("--trials", type=int, default=20)
    a.add_argument("--seed", type=int, default=7)
    a.add_argument("--verbose", action="store_true")
    a.set_defaults(func=cmd_bench)

    a = sp.add_parser("explain", help="explain a pair")
    a.add_argument("lost")
    a.add_argument("found")
    a.set_defaults(func=cmd_explain)

    a = sp.add_parser("reset", help="reset seed data")
    a.set_defaults(func=cmd_reset)

    a = sp.add_parser("test", help="run unit tests")
    a.set_defaults(func=cmd_test)

    args = p.parse_args(argv)
    if not getattr(args, "func", None):
        p.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main() or 0)