from __future__ import annotations
import time
from .models import Item

HOUR = 3600.0
NOW = time.time()


def seed_items() -> list[Item]:
    def m(type_, name, cat, desc, loc, ago_h, by, secret=""):
        return Item.new(
            type=type_, name=name, category=cat, description=desc,
            location_index=loc, timestamp=NOW - ago_h * HOUR,
            reported_by=by, secret=secret,
        )
    return [
        m("lost",  "Black leather wallet", "Wallet",
          "Black wallet with student ID and a blue library card inside",
          2, 5, "You", "photo of a golden retriever as ID photo"),
        m("found", "Black wallet", "Wallet",
          "Black leather wallet found on a reading table, has some cards",
          2, 3, "Arjun", "Library card with the name Kavya, a 500 rupee note"),
        m("found", "White earbuds case", "Earphones",
          "White wireless earbuds case with a small scratch",
          0, 20, "Meera", "Left bud missing"),
        m("lost",  "AirPods", "Earphones",
          "White wireless earphones in a case, lost after the physics lecture",
          0, 26, "Priya"),
        m("found", "Steel water bottle", "Water bottle",
          "Navy blue insulated bottle with a dent near the base",
          3, 8, "Rahul", "Sticker of a mountain on the bottom"),
        m("lost",  "Hostel room keys", "Keys",
          "Three keys on a red keychain with a bottle opener",
          4, 30, "Divya"),
        m("found", "Calculus textbook", "Books",
          "Thick maths textbook with yellow sticky notes",
          2, 50, "Sanjay", "Name Vikram on page 3"),
    ]