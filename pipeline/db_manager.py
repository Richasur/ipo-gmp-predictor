"""
db_manager.py — PostgreSQL connection + all DB operations via Supabase
"""

import os
import logging
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")


@contextmanager
def get_conn():
    """Context manager for a psycopg2 connection."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Insert helpers ────────────────────────────────────────────────────────────

def insert_gmp_records(records: list[dict]) -> int:
    """Bulk-insert raw GMP records. Returns number of rows inserted."""
    if not records:
        return 0

    cols = ["ipo_name", "gmp_price", "gmp_percent", "price_band",
            "est_listing_gain", "ipo_status", "source", "scraped_at"]

    rows = [
        (
            r.get("ipo_name"),
            r.get("gmp_price"),
            r.get("gmp_percent"),
            r.get("price_band"),
            r.get("est_listing_gain"),
            r.get("ipo_status"),
            r.get("source", "ipowatch"),
            r.get("scraped_at"),
        )
        for r in records
    ]

    sql = f"""
        INSERT INTO gmp_data ({", ".join(cols)})
        VALUES %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, sql, rows)
    logger.info(f"[DB] Inserted {len(rows)} gmp_data rows")
    return len(rows)


def insert_scores(score_results: list) -> int:
    """Insert scoring results into ipo_scores. Returns rows inserted."""
    if not score_results:
        return 0

    rows = [
        (
            s.ipo_name,
            s.score,
            s.signal,
            s.confidence,
            s.gmp_score,
            s.trend_score,
            s.status_score,
            s.listing_score,
            ", ".join(s.reasons),
        )
        for s in score_results
    ]

    sql = """
        INSERT INTO ipo_scores
            (ipo_name, score, signal, confidence,
             gmp_score, trend_score, status_score, listing_score, reasons)
        VALUES %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, sql, rows)
    logger.info(f"[DB] Inserted {len(rows)} ipo_scores rows")
    return len(rows)


def upsert_performance(perf_records: list[dict]) -> int:
    """
    Insert prediction-vs-actual records into ipo_performance.
    Each dict: ipo_name, predicted_gain, actual_gain
    """
    if not perf_records:
        return 0

    rows = []
    for p in perf_records:
        predicted  = p.get("predicted_gain", 0.0) or 0.0
        actual     = p.get("actual_gain",    0.0) or 0.0
        abs_error  = abs(predicted - actual)
        correct    = (predicted >= 0 and actual >= 0) or (predicted < 0 and actual < 0)
        rows.append((p["ipo_name"], predicted, actual, abs_error, correct))

    sql = """
        INSERT INTO ipo_performance
            (ipo_name, predicted_gain, actual_gain, abs_error, correct_direction)
        VALUES %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, sql, rows)
    logger.info(f"[DB] Inserted {len(rows)} ipo_performance rows")
    return len(rows)


# ── Fetch helpers ─────────────────────────────────────────────────────────────

def fetch_gmp_latest() -> list[dict]:
    """Return latest GMP record per IPO from gmp_latest view."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM gmp_latest ORDER BY ipo_name")
            return [dict(r) for r in cur.fetchall()]


def fetch_gmp_trend(ipo_name: str | None = None) -> list[dict]:
    """Return time-series GMP with delta for a specific IPO (or all)."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if ipo_name:
                cur.execute(
                    "SELECT * FROM gmp_trend WHERE ipo_name = %s ORDER BY scraped_at",
                    (ipo_name,)
                )
            else:
                cur.execute("SELECT * FROM gmp_trend ORDER BY ipo_name, scraped_at")
            return [dict(r) for r in cur.fetchall()]


def fetch_scores_latest() -> list[dict]:
    """Return latest score per IPO from ipo_scores_latest view."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM ipo_scores_latest ORDER BY score DESC")
            return [dict(r) for r in cur.fetchall()]


def fetch_score_history(ipo_name: str) -> list[dict]:
    """Return full score history for one IPO."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM ipo_scores WHERE ipo_name = %s ORDER BY scored_at",
                (ipo_name,)
            )
            return [dict(r) for r in cur.fetchall()]


def fetch_model_performance() -> dict:
    """Return aggregated model performance KPIs."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM model_performance_summary")
            row = cur.fetchone()
            return dict(row) if row else {}


def fetch_performance_history() -> list[dict]:
    """Return full prediction-vs-actual table."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM ipo_performance ORDER BY tracked_at DESC"
            )
            return [dict(r) for r in cur.fetchall()]


def fetch_raw_gmp_data(limit: int = 500) -> list[dict]:
    """Return raw GMP data (most recent rows)."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM gmp_data ORDER BY scraped_at DESC LIMIT %s",
                (limit,)
            )
            return [dict(r) for r in cur.fetchall()]
