"""
run_pipeline.py — Main entry point
Flow: scrape → merge → insert → score → track performance → alert
"""

import logging
import sys
import os

# Make sure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.ipowatch_scraper    import scrape_ipowatch
from scraper.chittorgarh_scraper import scrape_chittorgarh
from pipeline.db_manager         import (
    insert_gmp_records, insert_scores, upsert_performance,
    fetch_gmp_trend, fetch_scores_latest
)
from scorer.scoring_engine       import score_all
from utils.email_alerts          import send_strong_buy_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


def merge_sources(primary: list[dict], secondary: list[dict]) -> list[dict]:
    """
    Merge ipowatch (primary) and chittorgarh (secondary).
    Primary wins on name collision.
    """
    merged = {r["ipo_name"]: r for r in secondary}   # secondary first
    for r in primary:
        merged[r["ipo_name"]] = r                     # primary overwrites
    result = list(merged.values())
    logger.info(f"[merge] {len(primary)} ipowatch + {len(secondary)} chittorgarh → {len(result)} merged")
    return result


def build_performance_records(merged: list[dict], scores: list) -> list[dict]:
    """
    For each scored IPO, record predicted gain vs actual (if already listed).
    Only logs when ipo_status indicates listing has occurred.
    """
    perf = []
    status_map = {r["ipo_name"]: r.get("ipo_status", "") for r in merged}

    for s in scores:
        status = (status_map.get(s.ipo_name) or "").lower()
        if "listed" in status:
            # actual_gain would ideally come from live listing data;
            # here we use est_listing_gain as a proxy until actual is available.
            gain_map = {r["ipo_name"]: r.get("est_listing_gain", 0.0) for r in merged}
            perf.append({
                "ipo_name":      s.ipo_name,
                "predicted_gain": s.score / 40 * 30,  # rough linear map
                "actual_gain":   gain_map.get(s.ipo_name, 0.0),
            })
    return perf


def run():
    logger.info("=" * 60)
    logger.info("IPO GMP Pipeline starting")

    # ── Step 1: Scrape ─────────────────────────────────────
    ipowatch_data    = scrape_ipowatch()
    chittorgarh_data = scrape_chittorgarh()

    if not ipowatch_data and not chittorgarh_data:
        logger.error("Both scrapers returned empty data. Aborting.")
        sys.exit(1)

    # ── Step 2: Merge ──────────────────────────────────────
    merged = merge_sources(ipowatch_data, chittorgarh_data)

    # ── Step 3: Insert raw GMP ─────────────────────────────
    insert_gmp_records(merged)

    # ── Step 4: Fetch with LAG delta & score ───────────────
    trend_data = fetch_gmp_trend()   # from view with gmp_delta

    # Use latest entry per IPO for scoring
    latest_per_ipo: dict[str, dict] = {}
    for row in trend_data:
        name = row["ipo_name"]
        if name not in latest_per_ipo or row["scraped_at"] > latest_per_ipo[name]["scraped_at"]:
            latest_per_ipo[name] = row

    score_inputs = list(latest_per_ipo.values())
    scores       = score_all(score_inputs)

    # ── Step 5: Insert scores ──────────────────────────────
    insert_scores(scores)

    # ── Step 6: Track performance ──────────────────────────
    perf_records = build_performance_records(merged, scores)
    if perf_records:
        upsert_performance(perf_records)

    # ── Step 7: Email alert for STRONG BUY ────────────────
    strong_buys = [s for s in scores if s.signal == "STRONG BUY"]
    if strong_buys:
        logger.info(f"[alert] {len(strong_buys)} STRONG BUY signal(s) detected — sending email")
        send_strong_buy_alert(strong_buys)
    else:
        logger.info("[alert] No STRONG BUY signals this run")

    logger.info("Pipeline complete ✓")
    logger.info(f"  IPOs processed : {len(scores)}")
    logger.info(f"  STRONG BUY     : {len(strong_buys)}")
    logger.info(f"  Top pick       : {scores[0].ipo_name if scores else 'N/A'} "
                f"({scores[0].score}/40 {scores[0].signal})" if scores else "")
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
