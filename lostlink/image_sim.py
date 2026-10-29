from __future__ import annotations
from typing import List, Optional


def histogram_similarity(h1: Optional[List[float]],
                         h2: Optional[List[float]]) -> Optional[float]:
    """L1 distance between two normalized 64-bin colour histograms.

    The frontend already downsamples to 96x96 and quantises RGB to 4 bits per
    channel, producing a 64-bin probability vector. We treat that vector as a
    'colour signature' and compare with 1 - L1/2 (max L1 for probability
    vectors is 2). Returns None if either side is missing.
    """
    if not h1 or not h2 or len(h1) != len(h2):
        return None
    l1 = sum(abs(a - b) for a, b in zip(h1, h2))
    return max(0.0, 1.0 - l1 / 2.0)