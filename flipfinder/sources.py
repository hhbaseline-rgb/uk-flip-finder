"""Where deals come from: HotUKDeals RSS feeds and new eBay listings."""
import base64
import os
import re
import xml.etree.ElementTree as ET

import requests

UA = {"User-Agent": "uk-flip-finder/1.0 (+github)"}
PRICE_RE = re.compile(r"£\s?(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)")


def parse_price(text: str) -> float | None:
    m = PRICE_RE.search(text or "")
    return float(m.group(1).replace(",", "")) if m else None


def _delivery_from_text(text: str) -> float | None:
    t = (text or "").lower()
    if "free delivery" in t or "free shipping" in t or "free p&p" in t or "free postage" in t:
        return 0.0
    m = re.search(r"£\s?(\d+(?:\.\d{1,2})?)\s*(?:delivery|p&p|postage|shipping)", t)
    return float(m.group(1)) if m else None


# ---------------- HotUKDeals ----------------

def parse_hotukdeals(xml_text: str) -> list:
    deals = []
    root = ET.fromstring(xml_text)
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        guid = (item.findtext("guid") or link).strip()
        desc = re.sub(r"<[^>]+>", " ", item.findtext("description") or "")
        price, merchant, image = None, "", None
        # HotUKDeals puts merchant/price in a namespaced element, e.g.
        # <pepper:merchant name="Argos" price="£399.99"/>
        for el in item:
            tag = el.tag.split("}")[-1].lower()
            if tag == "merchant":
                merchant = el.get("name", "") or merchant
                price = parse_price(el.get("price", "")) or price
            if tag in ("content", "thumbnail") and el.get("url"):
                image = image or el.get("url")
        if price is None:
            price = parse_price(title)
        if price is None:
            continue
        deals.append({
            "source": "hotukdeals",
            "id": "hukd:" + guid,
            "title": title,
            "description": desc[:500],
            "price": price,
            "delivery": _delivery_from_text(title + " " + desc),
            "merchant": merchant,
            "url": link,
            "image": image,
        })
    return deals


def fetch_hotukdeals(feeds: list) -> list:
    deals = []
    for url in feeds:
        try:
            r = requests.get(url, headers=UA, timeout=20)
            r.raise_for_status()
            deals += parse_hotukdeals(r.text)
        except Exception as e:  # one bad feed shouldn't stop the run
            print(f"[hotukdeals] {url} failed: {e}")
    return deals


# ---------------- eBay (official Browse API) ----------------

EBAY_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"


def ebay_token() -> str | None:
    cid, secret = os.getenv("EBAY_CLIENT_ID"), os.getenv("EBAY_CLIENT_SECRET")
    if not cid or not secret:
        return None
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    r = requests.post(EBAY_TOKEN_URL, timeout=20,
                      headers={"Authorization": f"Basic {auth}",
                               "Content-Type": "application/x-www-form-urlencoded"},
                      data={"grant_type": "client_credentials",
                            "scope": "https://api.ebay.com/oauth/api_scope"})
    r.raise_for_status()
    return r.json()["access_token"]


def ebay_search(token: str, query: str, max_price: float | None = None,
                limit: int = 20, sort: str = "newlyListed") -> list:
    filters = ["buyingOptions:{FIXED_PRICE}", "itemLocationCountry:GB",
               "priceCurrency:GBP", "conditions:{NEW|USED}"]
    if max_price:
        filters.append(f"price:[1..{max_price:.0f}]")
    params = {"q": query, "limit": limit, "filter": ",".join(filters)}
    if sort:
        params["sort"] = sort
    r = requests.get(EBAY_SEARCH_URL, params=params, timeout=20,
                     headers={"Authorization": f"Bearer {token}",
                              "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB"})
    r.raise_for_status()
    return r.json().get("itemSummaries", [])


def ebay_to_deal(s: dict) -> dict:
    ship = None
    opts = s.get("shippingOptions") or []
    if opts and opts[0].get("shippingCost"):
        ship = float(opts[0]["shippingCost"].get("value", 0))
    seller = s.get("seller") or {}
    pos = seller.get("feedbackPercentage")
    return {
        "source": "ebay",
        "id": "ebay:" + s["itemId"],
        "title": s.get("title", ""),
        "description": s.get("shortDescription", "") + " " + s.get("condition", ""),
        "price": float(s["price"]["value"]),
        "delivery": ship,
        "merchant": "eBay - " + seller.get("username", "?"),
        "seller_feedback": seller.get("feedbackScore"),
        "seller_positive_pct": float(pos) if pos else None,
        "condition": s.get("condition", ""),
        "url": s.get("itemWebUrl", ""),
        "image": (s.get("image") or {}).get("imageUrl"),
    }


def fetch_ebay(watchlist: list, cfg: dict) -> list:
    try:
        token = ebay_token()
    except Exception as e:
        print(f"[ebay] token failed: {e}")
        return []
    if not token:
        print("[ebay] no EBAY_CLIENT_ID/SECRET set - skipping eBay")
        return []
    deals = []
    min_profit = cfg["thresholds"]["min_profit_gbp"]
    for item in watchlist:
        if not item.resale_gbp:
            continue
        try:
            results = ebay_search(token, item.search_query,
                                  max_price=item.resale_gbp - min_profit,
                                  limit=cfg["sources"]["ebay_results_per_item"])
            deals += [ebay_to_deal(s) for s in results]
        except Exception as e:
            print(f"[ebay] {item.id} failed: {e}")
    return deals
