"""Builds and sends the Telegram alert."""
import html
import os

import requests


def format_alert(deal: dict, item, ebay, vinted, flags: list) -> str:
    e = html.escape
    best = max([ebay, vinted], key=lambda b: b.profit)
    where = "eBay" if best.platform == "ebay" else "Vinted"
    lines = [
        f"🔥 <b>{e(item.name)}</b>",
        f"<i>{e(deal['title'][:180])}</i>",
        "",
        f"🛒 Buy: <b>£{deal['price']:.2f}</b> at {e(deal.get('merchant') or deal['source'])}",
        f"💷 Profit on eBay: <b>£{ebay.profit:.2f}</b> ({ebay.return_pct:.0f}% return)",
        f"💷 Profit on Vinted: <b>£{vinted.profit:.2f}</b> ({vinted.return_pct:.0f}% return)",
        f"👉 Best: list on <b>{where}</b>",
        "",
        f"<b>{where} breakdown</b>",
        *[e(l) for l in best.lines()],
        f"= <b>£{best.profit:.2f} profit</b>",
    ]
    if flags:
        lines += ["", "⚠️ <b>Check before buying</b>", *[f"• {e(f)}" for f in flags]]
    lines += ["", f'<a href="{e(deal["url"])}">Open deal</a>']
    return "\n".join(lines)


def format_listing_draft(item, ebay_price: float) -> str:
    title = item.name[:80]
    body = (f"{item.name}\n\nCondition: [new/used - describe]\n"
            f"What's included: [list everything]\n\n"
            f"Fast tracked dispatch from a UK seller. Securely packed.")
    return (f"📝 <b>Listing draft</b> (copy for eBay/Vinted)\n"
            f"<b>Title:</b> {html.escape(title)}\n"
            f"<b>Price:</b> £{ebay_price:.2f}\n"
            f"<b>Description:</b>\n{html.escape(body)}")


def send(text: str, image: str | None = None) -> bool:
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("---- (Telegram not set up, printing instead) ----\n" + text)
        return False
    base = f"https://api.telegram.org/bot{token}"
    try:
        if image and len(text) <= 1000:  # photo captions max ~1024 chars
            r = requests.post(f"{base}/sendPhoto", timeout=20, data={
                "chat_id": chat, "photo": image, "caption": text, "parse_mode": "HTML"})
            if r.ok:
                return True
        r = requests.post(f"{base}/sendMessage", timeout=20, data={
            "chat_id": chat, "text": text, "parse_mode": "HTML",
            "disable_web_page_preview": "false"})
        r.raise_for_status()
        return True
    except Exception as ex:
        print(f"[telegram] send failed: {ex}")
        return False
