"""
scoring_engine.py — Rule-based IPO scoring system
Max score: 40 points across 4 factors.
Signals: STRONG BUY / BUY / HOLD / WEAK / AVOID
"""

from dataclasses import dataclass, field
from typing import Optional

# ── Score weights ─────────────────────────────────────────
MAX_GMP_SCORE     = 15
MAX_TREND_SCORE   = 10
MAX_STATUS_SCORE  = 10
MAX_LISTING_SCORE = 5
MAX_TOTAL         = MAX_GMP_SCORE + MAX_TREND_SCORE + MAX_STATUS_SCORE + MAX_LISTING_SCORE  # 40

# ── Signal thresholds (out of 40) ─────────────────────────
SIGNAL_THRESHOLDS = {
    "STRONG BUY": 30,
    "BUY":        22,
    "HOLD":       15,
    "WEAK":       8,
    # Below 8 → AVOID
}


@dataclass
class ScoreResult:
    ipo_name:     str
    score:        float
    signal:       str
    confidence:   float          # 0–95 %
    gmp_score:    float
    trend_score:  float
    status_score: float
    listing_score: float
    reasons:      list[str] = field(default_factory=list)


def score_ipo(
    ipo_name:         str,
    gmp_percent:      Optional[float],
    gmp_delta:        Optional[float],   # change vs previous scrape
    ipo_status:       Optional[str],
    est_listing_gain: Optional[float],
) -> ScoreResult:
    """
    Score a single IPO.

    Parameters
    ----------
    ipo_name         : Company name
    gmp_percent      : Current GMP as % of price band
    gmp_delta        : gmp_percent − prev_gmp_percent (LAG delta)
    ipo_status       : 'Open' | 'Upcoming' | 'Closed' | 'Listed' etc.
    est_listing_gain : Estimated listing gain %

    Returns
    -------
    ScoreResult dataclass
    """
    gmp_percent      = gmp_percent      or 0.0
    gmp_delta        = gmp_delta        or 0.0
    est_listing_gain = est_listing_gain or 0.0
    ipo_status       = (ipo_status or "").strip().lower()

    reasons = []

    # ── Factor 1: GMP % strength (max 15) ────────────────
    if gmp_percent >= 50:
        gmp_score = 15
        reasons.append(f"Very strong GMP ({gmp_percent:.1f}%)")
    elif gmp_percent >= 30:
        gmp_score = 12
        reasons.append(f"Strong GMP ({gmp_percent:.1f}%)")
    elif gmp_percent >= 20:
        gmp_score = 10
        reasons.append(f"Moderate GMP ({gmp_percent:.1f}%)")
    elif gmp_percent >= 10:
        gmp_score = 7
        reasons.append(f"Low-moderate GMP ({gmp_percent:.1f}%)")
    elif gmp_percent >= 5:
        gmp_score = 4
        reasons.append(f"Weak GMP ({gmp_percent:.1f}%)")
    elif gmp_percent > 0:
        gmp_score = 2
        reasons.append(f"Negligible GMP (<5%)")
    elif gmp_percent == 0:
        gmp_score = 0
        reasons.append("Negligible GMP (<5%)")
    else:
        # Negative GMP
        gmp_score = 0
        reasons.append(f"Negative GMP ({gmp_percent:.1f}%)")

    # ── Factor 2: Trend direction (max 10) ───────────────
    if gmp_delta > 5:
        trend_score = 10
        reasons.append(f"Strong uptrend (Δ{gmp_delta:+.1f}%)")
    elif gmp_delta > 2:
        trend_score = 8
        reasons.append(f"Rising trend (Δ{gmp_delta:+.1f}%)")
    elif gmp_delta > 0:
        trend_score = 6
        reasons.append(f"Slightly rising (Δ{gmp_delta:+.1f}%)")
    elif gmp_delta == 0:
        trend_score = 5
        reasons.append("Stable / flat trend")
    elif gmp_delta > -2:
        trend_score = 3
        reasons.append(f"Slightly falling (Δ{gmp_delta:+.1f}%)")
    elif gmp_delta > -5:
        trend_score = 1
        reasons.append(f"Falling trend (Δ{gmp_delta:+.1f}%)")
    else:
        trend_score = 0
        reasons.append(f"Sharp downtrend (Δ{gmp_delta:+.1f}%)")

    # ── Factor 3: IPO status (max 10) ────────────────────
    if "open" in ipo_status:
        status_score = 10
        reasons.append("IPO is Open")
    elif "upcoming" in ipo_status:
        status_score = 7
        reasons.append("IPO is Upcoming")
    elif "listed" in ipo_status:
        status_score = 2
        reasons.append("IPO already Listed")
    elif "closed" in ipo_status:
        status_score = 3
        reasons.append("IPO Closed")
    else:
        status_score = 5
        reasons.append(f"IPO status: {ipo_status or 'Unknown'}")

    # ── Factor 4: Estimated listing gain (max 5) ─────────
    if est_listing_gain >= 50:
        listing_score = 5
        reasons.append(f"Exceptional listing gain ({est_listing_gain:.1f}%)")
    elif est_listing_gain >= 20:
        listing_score = 4
        reasons.append(f"Strong listing gain ({est_listing_gain:.1f}%)")
    elif est_listing_gain >= 10:
        listing_score = 3
        reasons.append(f"Moderate listing gain ({est_listing_gain:.1f}%)")
    elif est_listing_gain >= 5:
        listing_score = 2
        reasons.append(f"Weak listing gain ({est_listing_gain:.1f}%)")
    elif est_listing_gain > 0:
        listing_score = 1
        reasons.append(f"Minimal listing gain ({est_listing_gain:.1f}%)")
    else:
        listing_score = 0
        reasons.append(f"Weak listing gain ({est_listing_gain:.1f}%)")

    # ── Total score ───────────────────────────────────────
    total = gmp_score + trend_score + status_score + listing_score

    # ── Signal ────────────────────────────────────────────
    if total >= SIGNAL_THRESHOLDS["STRONG BUY"]:
        signal = "STRONG BUY"
    elif total >= SIGNAL_THRESHOLDS["BUY"]:
        signal = "BUY"
    elif total >= SIGNAL_THRESHOLDS["HOLD"]:
        signal = "HOLD"
    elif total >= SIGNAL_THRESHOLDS["WEAK"]:
        signal = "WEAK"
    else:
        signal = "AVOID"

    # ── Confidence (0–95%) ────────────────────────────────
    # Based on score ratio + bonus for strong trend / clear status
    base_confidence = (total / MAX_TOTAL) * 80
    bonus = 0
    if abs(gmp_delta) > 2:
        bonus += 5
    if "open" in ipo_status or "upcoming" in ipo_status:
        bonus += 5
    if gmp_percent > 10:
        bonus += 5
    confidence = min(95, round(base_confidence + bonus, 1))

    return ScoreResult(
        ipo_name      = ipo_name,
        score         = round(total, 1),
        signal        = signal,
        confidence    = confidence,
        gmp_score     = gmp_score,
        trend_score   = trend_score,
        status_score  = status_score,
        listing_score = listing_score,
        reasons       = reasons,
    )


def score_all(gmp_records: list[dict]) -> list[ScoreResult]:
    """
    Score a list of GMP records (as returned by gmp_trend view).
    Each record should have: ipo_name, gmp_percent, gmp_delta,
    ipo_status, est_listing_gain.
    """
    results = []
    for rec in gmp_records:
        result = score_ipo(
            ipo_name         = rec.get("ipo_name", ""),
            gmp_percent      = rec.get("gmp_percent"),
            gmp_delta        = rec.get("gmp_delta"),
            ipo_status       = rec.get("ipo_status"),
            est_listing_gain = rec.get("est_listing_gain"),
        )
        results.append(result)
    return sorted(results, key=lambda r: r.score, reverse=True)
