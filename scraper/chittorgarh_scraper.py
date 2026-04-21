"""
chittorgarh_scraper.py — Secondary GMP data source
Uses cloudscraper to bypass Cloudflare protection.
"""

import logging
from datetime import datetime

try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False
    import requests

from bs4 import BeautifulSoup
import pandas as pd

logger = logging.getLogger(__name__)
URL = "https://www.chittorgarh.com/report/ipo-gmp-grey-market-premium-today-live/92/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}


def scrape_chittorgarh() -> list[dict]:
    if HAS_CLOUDSCRAPER:
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
    else:
        scraper = requests.Session()
        scraper.headers.update(HEADERS)

    try:
        resp = scraper.get(URL, timeout=20)
        if resp.status_code != 200:
            logger.warning(f"[chittorgarh] HTTP {resp.status_code}")
            return []
    except Exception as e:
        logger.error(f"[chittorgarh] Request error: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    scraped_at = datetime.utcnow().isoformat()
    records = []

    for table in soup.find_all("table"):
        text = table.get_text().lower()
        if "gmp" in text and ("ipo" in text or "company" in text):
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            for row in rows[1:]:
                cols = row.find_all(["td","th"])
                if len(cols) < 3:
                    continue
                try:
                    name       = cols[0].get_text(strip=True)
                    price_band = _num(cols[1].get_text(strip=True))
                    gmp_price  = _num(cols[2].get_text(strip=True))
                    gmp_pct    = _pct(cols[3].get_text(strip=True)) if len(cols) > 3 else None
                    if gmp_pct is None and gmp_price and price_band and price_band > 0:
                        gmp_pct = round((gmp_price / price_band) * 100, 2)

                    status = "Unknown"
                    for i in range(4, min(len(cols), 8)):
                        t = cols[i].get_text(strip=True).lower()
                        if any(s in t for s in ["open","close","upcoming","listed"]):
                            status = cols[i].get_text(strip=True).title()
                            break

                    if not name or name.lower() in ("ipo name","company",""):
                        continue

                    records.append({
                        "ipo_name": name, "gmp_price": gmp_price,
                        "gmp_percent": gmp_pct or 0.0, "price_band": price_band,
                        "est_listing_gain": gmp_pct or 0.0, "ipo_status": status,
                        "source": "chittorgarh", "scraped_at": scraped_at,
                    })
                except Exception as e:
                    logger.debug(f"[chittorgarh] row err: {e}")
            break

    logger.info(f"[chittorgarh] Scraped {len(records)} IPOs")
    return records


def _num(text):
    if not text: return None
    for tok in text.replace("₹","").replace(",","").split():
        try: return float(tok)
        except ValueError: pass
    return None

def _pct(text):
    if not text: return None
    for tok in text.replace("%","").replace("₹","").split():
        try: return float(tok)
        except ValueError: pass
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    data = scrape_chittorgarh()
    print(pd.DataFrame(data).to_string() if data else "No data.")
