"""Run with:  python -m pytest -q   (or  python tests/test_bot.py)"""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flipfinder import profit, risk, scan, sources
from flipfinder.matcher import find_item, has_term
from flipfinder.settings import load_config, load_watchlist

CFG = load_config()
WL = load_watchlist()
PRICES = {"ps5-pro": 600, "dewalt-dcd796-body": 70, "dewalt-dcd796-kit": 200,
          "iphone-16-pro-256": 700, "makita-dhp485-body": 55}
for i in WL:
    if i.id in PRICES:
        i.resale_gbp = PRICES[i.id]


def item(id_):
    return next(i for i in WL if i.id == id_)


def test_term_boundaries():
    assert has_term("dewalt dcd796n 18v", "dcd796")
    assert not has_term("bosch professional drill", "pro")
    assert not has_term("iphone 160", "iphone 16")
    assert has_term("dewalt 5ah battery", "ah")
    assert not has_term("unlocked iphone", "locked")


def test_matching():
    assert find_item("PlayStation 5 Pro Console 2TB", WL).id == "ps5-pro"
    assert find_item("DeWalt DCD796N 18V XR Combi Drill Body Only", WL).id == "dewalt-dcd796-body"
    assert find_item("DeWalt DCD796 combi drill kit 2 x 5Ah batteries", WL).id == "dewalt-dcd796-kit"
    assert find_item("DualSense controller for PS5 Pro", WL) is None
    assert find_item("PS5 Pro faulty spares or repairs", WL) is None
    assert find_item("Bosch Professional GSB 18V-55 Solo", WL).id == "bosch-gsb18v55-body"
    assert find_item("Makita DHP485Z LXT", WL).id == "makita-dhp485-body"
    assert find_item("Apple iPhone 16 Pro 256GB Unlocked", WL).id == "iphone-16-pro-256"
    assert find_item("iPhone 16 Pro Max 256GB", WL) is None


def test_profit_every_cost_counts():
    b = profit.calculate(450.0, 0.0, item("ps5-pro"), CFG, "ebay")
    # 600 - 450 - (600*12.8% + 0.40) - postage 7.50 - tracked 2.50
    #   - insurance 4.00 - packaging 3.00 - returns 4% (24.00)
    expected = 600 - 450 - (76.80 + 0.40) - 7.50 - 2.50 - 4.00 - 3.00 - 24.00
    assert abs(b.profit - expected) < 0.01, (b.profit, expected)
    assert b.costs["Insurance"] == 4.00 and b.costs["Tracked + signed"] == 2.50


def test_vinted_buyer_pays_postage():
    v = profit.calculate(450.0, 0.0, item("ps5-pro"), CFG, "vinted")
    assert "Postage" not in v.costs
    expected = 600 - 450 - 30.0 - 3.00 - 24.00
    assert abs(v.profit - expected) < 0.01


def test_thresholds_block_thin_deals():
    b = profit.calculate(52.0, 0.0, item("dewalt-dcd796-body"), CFG, "ebay")
    assert not profit.passes(b, CFG)


def test_risk_flags():
    deal = {"title": "iPhone 16 Pro 256GB iCloud locked", "price": 200, "source": "ebay",
            "seller_feedback": 0, "seller_positive_pct": None}
    flags = risk.check(deal, item("iphone-16-pro-256"), CFG)
    joined = " ".join(flags)
    assert "lock" in joined and "too good" in joined and "low-feedback" in joined


HUKD_SAMPLE = """<?xml version="1.0"?>
<rss xmlns:pepper="http://www.pepper.com/rss" xmlns:media="http://search.yahoo.com/mrss/" version="2.0"><channel>
<item><title>PlayStation 5 Pro Console - £429.99 @ Argos</title>
<link>https://www.hotukdeals.com/deals/ps5-pro-1</link><guid>https://www.hotukdeals.com/deals/ps5-pro-1</guid>
<description>&lt;p&gt;Free delivery or click and collect&lt;/p&gt;</description>
<pepper:merchant name="Argos" price="£429.99"/>
<media:content url="https://images.example/ps5.jpg"/></item>
<item><title>DeWalt DCD796N 18V Combi Drill Body Only £49 Screwfix</title>
<link>https://www.hotukdeals.com/deals/dcd796-2</link><guid>https://www.hotukdeals.com/deals/dcd796-2</guid>
<description>Click and collect</description></item>
<item><title>Random kettle £9.99</title><link>https://x/3</link><guid>3</guid></item>
</channel></rss>"""


def test_hotukdeals_parse_and_full_run():
    deals = sources.parse_hotukdeals(HUKD_SAMPLE)
    assert len(deals) == 3
    assert deals[0]["price"] == 429.99 and deals[0]["merchant"] == "Argos"
    assert deals[0]["delivery"] == 0.0 and deals[0]["image"]
    assert deals[1]["price"] == 49.0 and deals[1]["delivery"] is None
    alerts = scan.run(deals=deals, cfg=CFG, watchlist=WL, dry_run=True)
    assert len(alerts) == 1 and "PS5 Pro" in alerts[0]
    print("\n===== SAMPLE ALERT =====\n" + alerts[0])


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
