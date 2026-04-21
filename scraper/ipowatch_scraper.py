"""
ipowatch_scraper.py — Primary GMP data source
Uses investorgain.com's internal JSON API (reverse-engineered from network traffic).
No Playwright or cloudscraper needed — plain requests to the API endpoint.
"""

import re
import logging
import requests
from datetime import datetime
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

API_URL = (
    "https://webnodejs.investorgain.com/cloud/new/report/data-read"
    "/331/1/4/2026/2026-27/0/all?search=&v=10-49"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.investorgain.com/",
    "Accept": "application/json, */*",
}


def scrape_ipowatch() -> list[dict]:
    """
    Fetch live GMP data from investorgain.com JSON API.
    Returns list of dicts with standardised schema.
    """
    try:
        resp = requests.get(API_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"[investorgain] API error: {e}")
        return []

    rows = data.get("reportTableData", [])
    if not rows:
        logger.warning("[investorgain] Empty reportTableData")
        return []

    scraped_at = datetime.utcnow().isoformat()
    records = []

    for row in rows:
        try:
            rec = _parse_row(row, scraped_at)
            if rec:
                records.append(rec)
        except Exception as e:
            logger.debug(f"[investorgain] Row parse error: {e}")

    logger.info(f"[investorgain] Scraped {len(records)} IPOs")
    return records


def _parse_row(row: dict, scraped_at: str) -> dict | None:
    # Clean IPO name (strip HTML tags)
    ipo_name = row.get("~ipo_name") or _strip_html(row.get("Name", ""))
    if not ipo_name:
        return None

    # Price band
    price_band = _num(row.get("Price (\u20b9)", ""))

    # GMP percent — already computed by their backend
    gmp_percent = _num(str(row.get("~gmp_percent_calc", "0")))

    # GMP price from the HTML field e.g. "₹5 (4.6%)"
    gmp_html  = row.get("GMP", "")
    gmp_price = _extract_gmp_price(gmp_html)

    # If gmp_percent missing, compute from price
    if not gmp_percent and gmp_price and price_band and price_band > 0:
        gmp_percent = round((gmp_price / price_band) * 100, 2)

    est_listing_gain = gmp_percent or 0.0

    # Status from open/close dates
    ipo_status = _derive_status(row)

    return {
        "ipo_name":         ipo_name,
        "gmp_price":        gmp_price,
        "gmp_percent":      gmp_percent or 0.0,
        "price_band":       price_band,
        "est_listing_gain": est_listing_gain,
        "ipo_status":       ipo_status,
        "source":           "investorgain",
        "scraped_at":       scraped_at,
    }


def _derive_status(row: dict) -> str:
    """Derive IPO status from open/close date fields."""
    from datetime import date
    today = date.today()

    def parse_date(s):
        if not s:
            return None
        for fmt in ("%Y-%m-%d", "%d-%b"):
            try:
                d = datetime.strptime(s, fmt).date()
                # Fix 2-field dates (no year) — assume current year
                if d.year == 1900:
                    d = d.replace(year=today.year)
                return d
            except ValueError:
                continue
        return None

    open_dt    = parse_date(row.get("~Srt_Open", ""))
    close_dt   = parse_date(row.get("~Srt_Close", ""))
    listing_dt = parse_date(row.get("~Str_Listing", ""))

    if listing_dt and today >= listing_dt:
        return "Listed"
    if open_dt and close_dt:
        if today < open_dt:
            return "Upcoming"
        if open_dt <= today <= close_dt:
            return "Open"
        if today > close_dt:
            return "Closed"
    return "Unknown"


def _extract_gmp_price(gmp_html: str) -> float | None:
    """Extract numeric GMP price from HTML like '&#8377;<b>5</b> (4.6%)'"""
    clean = _strip_html(gmp_html)
    # Look for a leading number before the first (
    m = re.match(r"[\u20b9₹\s]*([+-]?\d+\.?\d*)", clean.strip())
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def _strip_html(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text(strip=True)


def _num(text: str) -> float | None:
    if not text:
        return None
    text = str(text).replace("₹", "").replace(",", "").replace("\u20b9", "").strip()
    for tok in text.split():
        try:
            return float(tok)
        except ValueError:
            continue
    return None


if __name__ == "__main__":
    import pandas as pd
    logging.basicConfig(level=logging.INFO)
    data = scrape_ipowatch()
    print(pd.DataFrame(data).to_string() if data else "No data.")
