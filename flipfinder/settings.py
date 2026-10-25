"""Loads config.yaml and watchlist.csv."""
import csv
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_config(path: Path = ROOT / "config.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass
class WatchItem:
    id: str
    category: str
    name: str
    must_include: list  # list of groups; each group is a list of alternatives
    exclude: list
    resale_gbp: float | None
    size_band: str
    ebay_fee_pct: float | None
    notes: str = ""
    search_query: str = field(default="")


def _split(text: str, sep: str) -> list:
    return [t.strip().lower() for t in (text or "").split(sep) if t.strip()]


def _money(text: str) -> float | None:
    text = (text or "").replace("£", "").replace(",", "").strip()
    return float(text) if text else None


def load_watchlist(path: Path = ROOT / "watchlist.csv") -> list:
    items = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            groups = [_split(g, "|") for g in _split(row["must_include"], ";")]
            # Search query for eBay: first alternative from each group,
            # skipping descriptor groups ("body only", "kit"...) that only
            # help matching - eBay listings often say "DCD796N" instead.
            descriptors = {"body only", "bare", "kit", "2 x", "battery", "ah"}
            words = [g[0] for g in groups if g and not descriptors & set(g)]
            items.append(WatchItem(
                id=row["id"].strip(),
                category=row["category"].strip(),
                name=row["name"].strip(),
                must_include=groups,
                exclude=_split(row.get("exclude", ""), ";"),
                resale_gbp=_money(row.get("resale_gbp", "")),
                size_band=(row.get("size_band") or "medium").strip(),
                ebay_fee_pct=_money(row.get("ebay_fee_pct", "")),
                notes=(row.get("notes") or "").strip(),
                search_query=" ".join(words),
            ))
    return items
