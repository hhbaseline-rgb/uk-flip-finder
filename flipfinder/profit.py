"""The profit sum. Every cost comes off, so the profit is the profit."""
from dataclasses import dataclass, field


@dataclass
class Breakdown:
    platform: str
    resale: float
    buy_cost: float
    costs: dict = field(default_factory=dict)  # name -> £ (positive = cost)
    profit: float = 0.0
    return_pct: float = 0.0

    def lines(self) -> list:
        out = [f"Sells for: £{self.resale:.2f}"]
        for name, value in self.costs.items():
            if abs(value) < 0.005:
                continue
            sign = "+" if value < 0 else "-"
            out.append(f"{sign} {name}: £{abs(value):.2f}")
        return out


def _r(x: float) -> float:
    return round(x + 1e-9, 2)


def calculate(buy_price: float, delivery_to_you: float | None, item, cfg: dict,
              platform: str = "ebay") -> Breakdown:
    c, fees = cfg["costs"], cfg["fees"]
    resale = float(item.resale_gbp)
    band = cfg["size_bands"].get(item.size_band, cfg["size_bands"]["medium"])

    delivery = c["default_delivery_to_you_gbp"] if delivery_to_you is None else delivery_to_you
    costs = {
        "Buy price": buy_price,
        "Delivery to you": delivery,
        "Collection": c["collection_cost_gbp"],
    }

    if platform == "ebay":
        pct = item.ebay_fee_pct if item.ebay_fee_pct is not None else fees["ebay_default_pct"]
        costs["eBay fee"] = resale * pct / 100 + fees["ebay_per_order_gbp"]
        costs["Promoted listing"] = resale * c["promoted_listing_pct"] / 100
        seller_pays_postage = True
    else:  # vinted
        costs["Vinted fee"] = resale * fees["vinted_pct"] / 100
        seller_pays_postage = not fees.get("vinted_buyer_pays_postage", True)

    if seller_pays_postage:
        costs["Postage"] = band["postage"]
        if resale > c["tracked_signed_over_gbp"]:
            costs["Tracked + signed"] = c["tracked_signed_extra_gbp"]
        if resale > c["insurance_over_gbp"]:
            costs["Insurance"] = c["insurance_extra_gbp"]
    costs["Packaging"] = band["packaging"]
    costs["Returns allowance"] = resale * c["returns_allowance_pct"] / 100
    costs["Cashback"] = -(buy_price * c["cashback_pct"] / 100)

    costs = {k: _r(v) for k, v in costs.items()}
    buy_cost = _r(buy_price + delivery + c["collection_cost_gbp"])
    profit = _r(resale - sum(costs.values()))
    return_pct = round(profit / buy_cost * 100, 1) if buy_cost > 0 else 0.0
    return Breakdown(platform, resale, buy_cost, costs, profit, return_pct)


def passes(b: Breakdown, cfg: dict) -> bool:
    t = cfg["thresholds"]
    return b.profit >= t["min_profit_gbp"] and b.return_pct >= t["min_return_pct"]
