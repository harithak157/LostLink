import unittest

from lostlink.models import Item
from lostlink.matching import build_pair
from lostlink.rules import build_rules
from lostlink.inference import InferenceEngine
from lostlink.explanation import ExplanationFacility
from lostlink.search import best_first_assignment, greedy_assignment


def _mk(**kw):
    base = dict(name="X", category="Wallet", description="black wallet",
                location_index=2, timestamp=1000.0, reported_by="u")
    base.update(kw); return Item.new(**base)


class TestNLP(unittest.TestCase):
    def test_synonyms(self):
        from lostlink.nlp import tokenize
        self.assertIn("earphones", tokenize("airpods"))
        self.assertIn("bag", tokenize("backpack"))


class TestRules(unittest.TestCase):
    def test_high_conf_requires_image(self):
        l = _mk(type="lost", name="Black wallet", description="black wallet id")
        f = _mk(type="found", name="Black wallet", description="black wallet id",
                histogram=[1/64]*64)
        l.histogram = [1/64]*64
        ctx = build_pair(l, f)
        eng = InferenceEngine([ctx]); eng.run()
        self.assertTrue(eng.wm.has(f"high_conf_match({l.id},{f.id})"))

    def test_match_candidate_without_image(self):
        l = _mk(type="lost", name="Steel bottle", description="blue bottle")
        f = _mk(type="found", name="Steel bottle", description="blue bottle")
        eng = InferenceEngine([build_pair(l, f)]); eng.run()
        self.assertTrue(eng.wm.has(f"match_candidate({l.id},{f.id})"))


class TestExplanation(unittest.TestCase):
    def test_how_contains_rule(self):
        l = _mk(type="lost", name="Black wallet", description="black wallet")
        f = _mk(type="found", name="Black wallet", description="black wallet")
        eng = InferenceEngine([build_pair(l, f)]); eng.run()
        text = ExplanationFacility(eng).how(f"match_candidate({l.id},{f.id})")
        self.assertIn("because rule", text)


class TestSearch(unittest.TestCase):
    def test_heuristic_matches_optimal(self):
        cands = {"L1": [("F1", 0.9), ("F2", 0.8)],
                 "L2": [("F1", 0.85), ("F2", 0.7)]}
        a = best_first_assignment(cands)
        g = greedy_assignment(cands)
        # A* should find sum >= greedy
        self.assertGreaterEqual(a.cost, g.cost - 1e-9)

    def test_empty_candidates(self):
        r = best_first_assignment({})
        self.assertTrue(r.found)
        self.assertEqual(r.pairs, [])


if __name__ == "__main__":
    unittest.main()