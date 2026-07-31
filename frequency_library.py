"""Loads and searches the CAFL frequency library (data/cafl_frequencies.json)."""
import json
import os

_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "cafl_frequencies.json")
_cache = None


def _load():
    global _cache
    if _cache is None:
        with open(_DATA_PATH) as f:
            _cache = json.load(f)
    return _cache


def get_meta():
    data = _load()
    return {"source": data["source"], "disclaimer": data["disclaimer"]}


def get_categories():
    data = _load()
    cats = sorted(set(e["category"] for e in data["entries"]))
    return cats


def get_all_entries():
    return _load()["entries"]


def get_entry(slug: str):
    for e in _load()["entries"]:
        if e["slug"] == slug:
            return e
    return None


def search(query: str = "", category: str = ""):
    entries = _load()["entries"]
    q = (query or "").strip().lower()
    cat = (category or "").strip()

    def matches(e):
        if cat and e["category"] != cat:
            return False
        if q and q not in e["name"].lower() and q not in e["category"].lower():
            return False
        return True

    return [e for e in entries if matches(e)]
