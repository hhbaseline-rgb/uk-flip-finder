"""Red flags shown on every alert. Flags warn you - they don't block."""
from .matcher import has_term, _normalise

PHONE_LOCK_WORDS = ["icloud", "locked", "activation lock", "blacklisted", "blocked",
                    "network locked", "on contract", "finance", "bad imei", "fmi on"]
CONDITION_WORDS = ["read description", "see description", "untested", "no returns",
                   "sold as seen", "cracked", "dead pixel", "drift"]
TOOL_WORDS = ["no charger", "no battery", "battery not included", "copy", "compatible"]


def check(deal: dict, item, cfg: dict) -> list:
    text = _normalise(" ".join([deal.get("title", ""), deal.get("description", "")]))
    flags = []
    r = cfg["risk"]

    if item.category in ("phone", "tablet", "watch", "laptop"):
        hits = [w for w in PHONE_LOCK_WORDS if has_term(text, w)]
        if hits:
            flags.append("Possible lock/finance issue: " + ", ".join(hits))

    hits = [w for w in CONDITION_WORDS if has_term(text, w)]
    if hits:
        flags.append("Condition warning: " + ", ".join(hits))

    if item.category == "tool":
        hits = [w for w in TOOL_WORDS if has_term(text, w)]
        if hits:
            flags.append("Check what's included: " + ", ".join(hits))

    if item.resale_gbp and deal.get("price"):
        below = (1 - deal["price"] / item.resale_gbp) * 100
        if below >= r["too_cheap_pct"]:
            flags.append(f"{below:.0f}% under resale - too good to be true? Likely scam or price error")

    fb = deal.get("seller_feedback")
    if fb is not None and fb < r["min_seller_feedback"]:
        flags.append(f"New/low-feedback seller ({fb})")
    pos = deal.get("seller_positive_pct")
    if pos is not None and pos < r["min_seller_positive_pct"]:
        flags.append(f"Seller positive feedback only {pos}%")

    if deal.get("source") == "hotukdeals" and deal.get("delivery") is None:
        flags.append("Delivery cost not stated - check before buying")

    if item.notes:
        flags.append(item.notes)
    return flags
