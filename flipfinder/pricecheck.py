"""Weekly price check: compares your resale prices with what the same
items are currently listed for on eBay UK, and tells you which to update.

eBay's free API shows live asking prices, not sold prices - so treat the
figure as a guide and confirm against eBay sold listings before changing.

Run:  python -m flipfinder.pricecheck
"""
import statistics

from . import sources, telegram
from .matcher import matches
from .settings import load_config, load_watchlist

MOVE_PCT = 10  # flag anything that's drifted more than this


def check_item(token: str, item) -> dict:
    results = sources.ebay_search(token, item.search_query, limit=50, sort="")
    prices = [float(s["price"]["value"]) for s in results
              if matches(s.get("title", ""), item)]
    if len(prices) < 3:
        return {"item": item, "median": None, "count": len(prices)}
    return {"item": item, "median": round(statistics.median(prices), 2),
            "count": len(prices)}


def report(rows: list) -> list:
    msgs, lines = [], ["📊 <b>Weekly price check</b> (eBay asking prices)", ""]
    for r in rows:
        item, med = r["item"], r["median"]
        if med is None:
            lines.append(f"• {item.name}: not enough listings ({r['count']})")
        elif not item.resale_gbp:
            lines.append(f"• {item.name}: <b>no resale price set</b> - "
                         f"eBay median £{med:.0f} ({r['count']} listings)")
        else:
            diff = (med - item.resale_gbp) / item.resale_gbp * 100
            if abs(diff) >= MOVE_PCT:
                arrow = "⬆️" if diff > 0 else "⬇️"
                lines.append(f"• {arrow} {item.name}: yours £{item.resale_gbp:.0f}, "
                             f"eBay now £{med:.0f} ({diff:+.0f}%)")
    if len(lines) == 2:
        lines.append("All resale prices are within 10% of eBay. Nothing to change.")
    # Telegram messages max 4096 chars - split if needed
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) > 3800:
            msgs.append(chunk)
            chunk = ""
        chunk += line + "\n"
    msgs.append(chunk)
    return msgs


def run():
    load_config()
    token = sources.ebay_token()
    if not token:
        print("No eBay keys set - can't run price check.")
        return
    rows = []
    for item in load_watchlist():
        try:
            rows.append(check_item(token, item))
        except Exception as e:
            print(f"[pricecheck] {item.id} failed: {e}")
    for m in report(rows):
        telegram.send(m)


if __name__ == "__main__":
    run()
