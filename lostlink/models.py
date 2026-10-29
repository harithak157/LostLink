from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import time, uuid


@dataclass
class Item:
    id: str
    type: str                      # "lost" | "found"
    name: str
    category: str
    description: str
    location_index: int
    timestamp: float               # unix seconds
    reported_by: str
    secret: str = ""
    status: str = "open"           # open | pending | returned
    thumbnail: Optional[str] = None
    histogram: Optional[List[float]] = None
    created_at: float = field(default_factory=time.time)

    @staticmethod
    def new(**kw) -> "Item":
        kw.setdefault("id", "i" + uuid.uuid4().hex[:10])
        return Item(**kw)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Item":
        fields = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in fields})


@dataclass
class Claim:
    id: str
    item_id: str
    claimant: str
    proof: str
    status: str = "pending"        # pending | approved | rejected
    created_at: float = field(default_factory=time.time)

    @staticmethod
    def new(**kw) -> "Claim":
        kw.setdefault("id", "c" + uuid.uuid4().hex[:10])
        return Claim(**kw)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Claim":
        fields = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in fields})


@dataclass
class PairContext:
    """All heuristic signals computed once for a (lost, found) pair."""
    lost: Item
    found: Item
    cat_same: bool
    text_sim: float
    loc_sim: float
    time_sim: float
    img_sim: Optional[float]

    def score(self) -> float:
        """Final ranking score. Image weight shifts when histograms exist."""
        if self.img_sim is None:
            return 0.55 * self.text_sim + 0.25 * self.loc_sim + 0.20 * self.time_sim
        return 0.40 * self.text_sim + 0.25 * self.img_sim + 0.20 * self.loc_sim + 0.15 * self.time_sim

    def signals(self) -> Dict[str, float]:
        d = {"text": self.text_sim, "location": self.loc_sim, "time": self.time_sim}
        if self.img_sim is not None:
            d["image"] = self.img_sim
        return d