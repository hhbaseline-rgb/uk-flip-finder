"""Main run: fetch deals -> match -> profit sum -> risk check -> alert.

Run:  python -m flipfinder.scan
"""
import json
import time
from pathlib import Path

from . import profit, risk, sources, telegram
from .matcher import find_item
from .settings import ROOT, load_config, load_watchlist

STATE_FILE = ROOT / "state" / "seen.json"
KEEP_DAYS = 14


def load_seen() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def save_seen(seen: dict) -> None:
    cutoff = time.time() - KEEP_DAYS * 86400
    seen = {k: v for k, v in seen.items() if v >= cutoff}
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(seen, indent=0, sort_keys=True))


def evaluate(deal: dict, watchlist: list, cfg: dict):
    """Return (item, ebay_breakdown, vinted_breakdown, flags) or None."""
    item = find_item(deal["title"], watchlist)
    if not item or not item.resale_gbp:
        return None
    ebay = profit.calculate(deal["price"], deal.get("delivery"), item, cfg, "ebay")
    vinted = profit.calculate(deal["price"], deal.get("delivery"), item, cfg, "vinted")
    if not (profit.passes(ebay, cfg) or profit.passes(vinted, cfg)):
        return None
    return item, ebay, vinted, risk.check(deal, item, cfg)


def run(deals: list | None = None, cfg: dict | None = None,
        watchlist: list | None = None, dry_run: bool = False) -> list:
    cfg = cfg or load_config()
    watchlist = watchlist or load_watchlist()
    priced = [i for i in watchlist if i.resale_gbp]
    print(f"Watchlist: {len(watchlist)} items, {len(priced)} with a resale price set")

    if deals is None:
        deals = sources.fetch_hotukdeals(cfg["sources"]["hotukdeals_feeds"])
        if cfg["sources"].get("ebay_new_listings"):
            deals += sources.fetch_ebay(watchlist, cfg)
    print(f"Deals fetched: {len(deals)}")

    seen = {} if dry_run else load_seen()
    alerts = []
    for deal in deals:
        if deal["id"] in seen:
            continue
        result = evaluate(deal, watchlist, cfg)
        if not result:
            continue
        item, ebay, vinted, flags = result
        text = telegram.format_alert(deal, item, ebay, vinted, flags)
        alerts.append(text)
        if not dry_run:
            telegram.send(text, deal.get("image"))
            telegram.send(telegram.format_listing_draft(item, item.resale_gbp))
            seen[deal["id"]] = time.time()

    if not dry_run:
        save_seen(seen)
    print(f"Alerts sent: {len(alerts)}")
    return alerts


if __name__ == "__main__":
    run()
