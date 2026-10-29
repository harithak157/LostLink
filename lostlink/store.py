from __future__ import annotations
import json, os, threading
from typing import Dict, List

from .models import Item, Claim
from . import seed

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
ITEMS_FILE = os.path.join(DATA_DIR, "items.json")
CLAIMS_FILE = os.path.join(DATA_DIR, "claims.json")

_LOCK = threading.RLock()


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _read(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def _write(path, data):
    _ensure_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


class Store:
    def __init__(self):
        with _LOCK:
            items = _read(ITEMS_FILE)
            if not items:
                items = [i.to_dict() for i in seed.seed_items()]
                _write(ITEMS_FILE, items)
            claims = _read(CLAIMS_FILE) or []
        self.items: Dict[str, Item] = {i["id"]: Item.from_dict(i) for i in items}
        self.claims: Dict[str, Claim] = {c["id"]: Claim.from_dict(c) for c in claims}

    # ---------------- items
    def list_items(self) -> List[Item]:
        return sorted(self.items.values(), key=lambda i: i.created_at, reverse=True)

    def get_item(self, iid: str) -> Item | None:
        return self.items.get(iid)

    def add_item(self, item: Item) -> Item:
        with _LOCK:
            self.items[item.id] = item
            self._flush_items()
        return item

    def update_item(self, iid: str, **changes) -> Item | None:
        with _LOCK:
            it = self.items.get(iid)
            if not it:
                return None
            for k, v in changes.items():
                if hasattr(it, k):
                    setattr(it, k, v)
            self._flush_items()
            return it

    def delete_item(self, iid: str) -> bool:
        with _LOCK:
            if iid in self.items:
                del self.items[iid]
                self._flush_items()
                return True
            return False

    # ---------------- claims
    def list_claims(self) -> List[Claim]:
        return sorted(self.claims.values(), key=lambda c: c.created_at, reverse=True)

    def get_claim(self, cid: str) -> Claim | None:
        return self.claims.get(cid)

    def add_claim(self, claim: Claim) -> Claim:
        with _LOCK:
            self.claims[claim.id] = claim
            self._flush_claims()
        return claim

    def update_claim(self, cid: str, **changes) -> Claim | None:
        with _LOCK:
            c = self.claims.get(cid)
            if not c:
                return None
            for k, v in changes.items():
                if hasattr(c, k):
                    setattr(c, k, v)
            if c.status == "approved":
                it = self.items.get(c.item_id)
                if it:
                    it.status = "returned"
                    self._flush_items()
            self._flush_claims()
            return c

    # ---------------- persistence
    def _flush_items(self):
        _write(ITEMS_FILE, [i.to_dict() for i in self.items.values()])

    def _flush_claims(self):
        _write(CLAIMS_FILE, [c.to_dict() for c in self.claims.values()])

    def reset(self):
        with _LOCK:
            self.items = {i.id: i for i in seed.seed_items()}
            self.claims = {}
            self._flush_items()
            self._flush_claims()