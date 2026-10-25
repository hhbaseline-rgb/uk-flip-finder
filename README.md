# UK Flip Finder

A bot that finds underpriced **electronics, consoles and branded power tools** online, works out the **true profit after every cost**, and sends a Telegram alert when a deal is worth buying to resell on eBay or Vinted.

It runs itself every 15 minutes on GitHub Actions. No server, no monthly bill.

---

## The problem

Good resale deals (price drops, price errors, people underpricing on eBay) disappear in minutes. Checking by hand means you miss most of them. And when you do find one, it's easy to forget a cost — fees, postage, packaging, returns — and a "£40 profit" turns into £8.

## What it does

1. **Watches for deals** — HotUKDeals feeds (Argos, Currys, Screwfix, Amazon and others) and brand-new eBay UK listings, via eBay's official API.
2. **Matches each deal to an exact item** on the watchlist — e.g. it knows a DeWalt *DCD796N* is the body-only drill and won't confuse it with the kit with batteries, or treat a PS5 controller as a PS5.
3. **Runs the full profit sum** — buy price, delivery, collection, platform fee, promoted listing, postage by parcel size, tracked & signed-for over £100, insurance over £300, packaging, a returns allowance, minus any cashback.
4. **Flags risks** — iCloud/network locks, "spares or repairs", missing batteries, brand-new sellers, and prices so low they're likely a scam.
5. **Alerts on Telegram** with profit on both eBay and Vinted, which is better, the full cost breakdown, and a listing draft.
6. **Weekly price check** — compares your resale prices with what eBay is showing now and tells you which to update.

Example alert:

```
🔥 PS5 Pro
🛒 Buy: £429.99 at Argos
💷 Profit on eBay: £51.81 (12% return)
💷 Profit on Vinted: £113.01 (26% return)
👉 Best: list on Vinted

Sells for: £600.00
- Buy price: £429.99
- Vinted fee: £30.00
- Packaging: £3.00
- Returns allowance: £24.00
= £113.01 profit
```

## How it's built

| Part | File |
|---|---|
| Settings — every cost and threshold | `config.yaml` |
| The items to hunt, with resale price and parcel size | `watchlist.csv` |
| Deal sources (HotUKDeals, eBay API) | `flipfinder/sources.py` |
| Title → exact item matching | `flipfinder/matcher.py` |
| The profit sum | `flipfinder/profit.py` |
| Risk flags | `flipfinder/risk.py` |
| Telegram alerts | `flipfinder/telegram.py` |
| Main run | `flipfinder/scan.py` |
| Weekly price check | `flipfinder/pricecheck.py` |
| Schedules | `.github/workflows/` |
| Tests with sample deals | `tests/test_bot.py` |

---

## Setup

### 1. Secrets (Settings → Secrets and variables → Actions → New repository secret)

| Name | Where from |
|---|---|
| `TELEGRAM_BOT_TOKEN` | @BotFather on Telegram |
| `TELEGRAM_CHAT_ID` | your chat ID (message your bot, then open `https://api.telegram.org/bot<TOKEN>/getUpdates`) |
| `EBAY_CLIENT_ID` | developer.ebay.com → Application Keys → **Production** App ID |
| `EBAY_CLIENT_SECRET` | same page → Production Cert ID |

Without the eBay keys the bot still runs on HotUKDeals alone.

### 2. Fill in `watchlist.csv`

For each item, put what it **actually sells for** in `resale_gbp` (check eBay → filter **Sold items**). Items with no resale price are skipped. The weekly price check will suggest a figure for blank ones.

`must_include` uses `;` between required terms and `|` between alternatives — e.g. `dcd796;body only|bare|dcd796n` means "must say DCD796 AND one of body only / bare / DCD796N".

### 3. Check `config.yaml`

Confirm the eBay business fee and Vinted Pro fee, and swap the postage/packaging figures for your own courier quotes.

### 4. Turn it on

Actions tab → enable workflows → open **Deal scan** → **Run workflow** to test straight away.

---

## Notes

- GitHub can delay scheduled runs by a few minutes at busy times.
- eBay's free API allows 5,000 searches a day. 40 items every 15 minutes is about 3,840 — fine, but if the watchlist grows past ~50 priced items, change the scan to every 20 minutes.
- Profit shown is before income tax.
