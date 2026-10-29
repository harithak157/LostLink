from __future__ import annotations
import json, os, re, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from lostlink.store import Store
from lostlink.models import Item, Claim
from lostlink.matching import build_pair
from lostlink.inference import InferenceEngine
from lostlink.explanation import ExplanationFacility
from lostlink.search import best_first_assignment, greedy_assignment
from lostlink.evaluation import benchmark

ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(ROOT, "static")

STORE = Store()


def _json(handler, status, payload):
    body = json.dumps(payload, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_body(handler) -> dict:
    n = int(handler.headers.get("Content-Length", "0") or "0")
    if not n:
        return {}
    raw = handler.rfile.read(n).decode("utf-8")
    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return {}


def _candidates_and_engine(lost: Item):
    found = [i for i in STORE.list_items()
             if i.type == "found" and i.status != "returned" and i.id != lost.id]
    contexts = [build_pair(lost, f) for f in found]
    engine = InferenceEngine(contexts)
    engine.run()
    return contexts, engine


class Handler(BaseHTTPRequestHandler):
    server_version = "LostLink/1.0"

    # -------------------------------------------------------- routes
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            return self._serve_file("index.html", "text/html")
        if path in ("/offline", "/LostLink.html"):
            return self._serve_file("LostLink.html", "text/html")
        if path.startswith("/static/"):
            return self._serve_file(path[len("/static/"):], None)

        if path == "/api/items":
            return _json(self, 200, {"items": [i.to_dict() for i in STORE.list_items()]})
        if path == "/api/claims":
            return _json(self, 200, {"claims": [c.to_dict() for c in STORE.list_claims()]})
        if path == "/api/stats":
            return _json(self, 200, self._stats())
        if path == "/api/bench":
            return _json(self, 200, self._bench())

        m = re.fullmatch(r"/api/items/([^/]+)", path)
        if m:
            it = STORE.get_item(m.group(1))
            if not it:
                return _json(self, 404, {"error": "not found"})
            return _json(self, 200, {"item": it.to_dict()})

        m = re.fullmatch(r"/api/matches/([^/]+)", path)
        if m:
            return self._matches(m.group(1))

        if path == "/api/explain":
            lost = (qs.get("lost") or [""])[0]
            found = (qs.get("found") or [""])[0]
            return self._explain(lost, found)

        return _json(self, 404, {"error": "unknown path"})

    def do_POST(self):
        path = urlparse(self.path).path
        body = _read_body(self)

        if path == "/api/items":
            try:
                it = Item.new(
                    type=body["type"], name=body["name"],
                    category=body["category"], description=body["description"],
                    location_index=int(body.get("location_index", 0)),
                    timestamp=float(body.get("timestamp") or 0) or 0,
                    reported_by=body.get("reported_by") or "Anonymous",
                    secret=body.get("secret") or "",
                    thumbnail=body.get("thumbnail"),
                    histogram=body.get("histogram"),
                )
            except KeyError as e:
                return _json(self, 400, {"error": f"missing field {e}"})
            STORE.add_item(it)
            return _json(self, 201, {"item": it.to_dict()})

        if path == "/api/claims":
            try:
                c = Claim.new(
                    item_id=body["item_id"],
                    claimant=body.get("claimant") or "Anonymous",
                    proof=body["proof"],
                )
            except KeyError as e:
                return _json(self, 400, {"error": f"missing field {e}"})
            STORE.add_claim(c)
            return _json(self, 201, {"claim": c.to_dict()})

        if path == "/api/reset":
            STORE.reset()
            return _json(self, 200, {"ok": True})

        return _json(self, 404, {"error": "unknown path"})

    def do_PATCH(self):
        path = urlparse(self.path).path
        body = _read_body(self)

        m = re.fullmatch(r"/api/items/([^/]+)", path)
        if m:
            it = STORE.update_item(m.group(1), **body)
            if not it:
                return _json(self, 404, {"error": "not found"})
            return _json(self, 200, {"item": it.to_dict()})

        m = re.fullmatch(r"/api/claims/([^/]+)", path)
        if m:
            c = STORE.update_claim(m.group(1), **body)
            if not c:
                return _json(self, 404, {"error": "not found"})
            return _json(self, 200, {"claim": c.to_dict()})

        return _json(self, 404, {"error": "unknown path"})

    def do_DELETE(self):
        path = urlparse(self.path).path
        m = re.fullmatch(r"/api/items/([^/]+)", path)
        if m:
            ok = STORE.delete_item(m.group(1))
            return _json(self, 200 if ok else 404, {"ok": ok})
        return _json(self, 404, {"error": "unknown path"})

    # ------------------------------------------------------ helpers
    def _serve_file(self, name, ctype):
        full = os.path.join(STATIC, name)
        if not os.path.isfile(full):
            return _json(self, 404, {"error": f"missing {name}"})
        with open(full, "rb") as f:
            data = f.read()
        ctype = ctype or ("text/html; charset=utf-8" if name.endswith(".html")
                          else "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _matches(self, lost_id):
        lost = STORE.get_item(lost_id)
        if not lost:
            return _json(self, 404, {"error": "lost item not found"})
        contexts, engine = _candidates_and_engine(lost)
        from lostlink.explanation import ExplanationFacility
        expl = ExplanationFacility(engine)
        # rank by score
        contexts.sort(key=lambda c: c.score(), reverse=True)
        matches = []
        for c in contexts:
            confidence = "weak"
            fact_hi = f"high_conf_match({lost.id},{c.found.id})"
            fact_lk = f"likely_match({lost.id},{c.found.id})"
            fact_cd = f"match_candidate({lost.id},{c.found.id})"
            if engine.wm.has(fact_hi):
                confidence = "high"
            elif engine.wm.has(fact_lk):
                confidence = "likely"
            elif engine.wm.has(fact_cd):
                confidence = "candidate"
            else:
                continue
            matches.append({
                "found": c.found.to_dict(),
                "score": round(c.score(), 4),
                "confidence": confidence,
                "breakdown": {k: round(v, 4) for k, v in c.signals().items()},
                "reason": self._reason(engine, lost.id, c.found.id),
            })
        return _json(self, 200, {
            "lost_id": lost_id,
            "matches": matches,
            "trace": [f.__dict__ for f in engine.trace],
            "inference_summary": {
                "rules_fired": len(engine.trace),
                "facts": len(engine.wm),
            },
        })

    def _reason(self, engine, lost_id, found_id):
        for pred in ("high_conf_match", "likely_match", "match_candidate"):
            fact = f"{pred}({lost_id},{found_id})"
            j = engine.wm.justification(fact)
            if j and not j.is_given:
                return f"{pred} via {j.rule_id}"
        return "not established"

    def _explain(self, lost_id, found_id):
        lost = STORE.get_item(lost_id)
        found = STORE.get_item(found_id)
        if not lost or not found:
            return _json(self, 404, {"error": "item not found"})
        ctx = build_pair(lost, found)
        engine = InferenceEngine([ctx])
        engine.run()
        expl = ExplanationFacility(engine)
        target = f"match_candidate({lost_id},{found_id})"
        if not engine.wm.has(target):
            target = f"likely_match({lost_id},{found_id})"
        if not engine.wm.has(target):
            target = f"high_conf_match({lost_id},{found_id})"
        return _json(self, 200, {
            "target": target,
            "how": expl.how(target),
            "why": expl.why(target),
            "why_not": expl.why_not(target),
            "trace": [f.__dict__ for f in engine.trace],
            "facts": engine.wm.facts(),
        })

    def _stats(self):
        items = STORE.list_items()
        open_lost = [i for i in items if i.type == "lost" and i.status == "open"]
        open_found = [i for i in items if i.type == "found" and i.status == "open"]
        returned = [i for i in items if i.status == "returned"]
        pending = [c for c in STORE.list_claims() if c.status == "pending"]
        with_matches = 0
        for l in open_lost:
            ctx, eng = _candidates_and_engine(l)
            if any(eng.wm.has(f"match_candidate({l.id},{c.found.id})") for c in ctx):
                with_matches += 1
        return {
            "open_lost": len(open_lost),
            "open_found": len(open_found),
            "returned": len(returned),
            "pending_claims": len(pending),
            "with_matches": with_matches,
        }

    def _bench(self):
        items = STORE.list_items()
        lost = [i for i in items if i.type == "lost" and i.status == "open"]
        found = [i for i in items if i.type == "found" and i.status == "open"]
        # Ground truth is a heuristic target derived from the seed data: for the
        # demo we match names pairwise where possible.
        truth = {}
        for l in lost:
            best, bs = None, 0.0
            for f in found:
                s = build_pair(l, f).score()
                if s > bs:
                    best, bs = f.id, s
            if best:
                truth[l.id] = best
        report = benchmark(lost, found, truth, trials=20, seed=7, verbose=False)
        return {"report": report}

    def log_message(self, fmt, *args):
        sys.stderr.write("[server] " + fmt % args + "\n")


def main(host="127.0.0.1", port=8000):
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"LostLink running at http://{host}:{port}/  (API at /api/*)")
    print(f"Offline demo at http://{host}:{port}/offline")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()