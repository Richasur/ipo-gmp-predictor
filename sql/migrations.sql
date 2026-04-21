-- ============================================================
-- IPO GMP Predictor — Full Database Schema
-- Run this in your Supabase SQL Editor
-- ============================================================

-- 1. Raw time-series GMP records
CREATE TABLE IF NOT EXISTS gmp_data (
    id              BIGSERIAL PRIMARY KEY,
    ipo_name        TEXT NOT NULL,
    gmp_price       NUMERIC,
    gmp_percent     NUMERIC,
    price_band      NUMERIC,
    est_listing_gain NUMERIC,
    ipo_status      TEXT,
    source          TEXT DEFAULT 'ipowatch',
    scraped_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Score history per IPO (append-only, no overwrite)
CREATE TABLE IF NOT EXISTS ipo_scores (
    id              BIGSERIAL PRIMARY KEY,
    ipo_name        TEXT NOT NULL,
    score           NUMERIC,
    signal          TEXT,
    confidence      NUMERIC,
    gmp_score       NUMERIC,
    trend_score     NUMERIC,
    status_score    NUMERIC,
    listing_score   NUMERIC,
    reasons         TEXT,
    scored_at       TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Predicted vs actual gain tracking
CREATE TABLE IF NOT EXISTS ipo_performance (
    id              BIGSERIAL PRIMARY KEY,
    ipo_name        TEXT NOT NULL,
    predicted_gain  NUMERIC,
    actual_gain     NUMERIC,
    abs_error       NUMERIC,
    correct_direction BOOLEAN,
    tracked_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- VIEWS
-- ============================================================

-- Latest GMP record per IPO
CREATE OR REPLACE VIEW gmp_latest AS
SELECT DISTINCT ON (ipo_name)
    id, ipo_name, gmp_price, gmp_percent, price_band,
    est_listing_gain, ipo_status, source, scraped_at
FROM gmp_data
ORDER BY ipo_name, scraped_at DESC;

-- Time-series with LAG delta
CREATE OR REPLACE VIEW gmp_trend AS
SELECT
    id,
    ipo_name,
    gmp_percent,
    price_band,
    est_listing_gain,
    ipo_status,
    scraped_at,
    LAG(gmp_percent) OVER (PARTITION BY ipo_name ORDER BY scraped_at) AS prev_gmp,
    gmp_percent - LAG(gmp_percent) OVER (PARTITION BY ipo_name ORDER BY scraped_at) AS gmp_delta
FROM gmp_data;

-- Latest score per IPO
CREATE OR REPLACE VIEW ipo_scores_latest AS
SELECT DISTINCT ON (ipo_name)
    id, ipo_name, score, signal, confidence,
    gmp_score, trend_score, status_score, listing_score,
    reasons, scored_at
FROM ipo_scores
ORDER BY ipo_name, scored_at DESC;

-- Model performance summary KPIs
CREATE OR REPLACE VIEW model_performance_summary AS
SELECT
    COUNT(*)                                        AS predictions_tracked,
    ROUND(AVG(CASE WHEN correct_direction THEN 1.0 ELSE 0.0 END) * 100, 1) AS direction_accuracy,
    ROUND(AVG(abs_error), 2)                        AS avg_absolute_error,
    MIN(tracked_at)::DATE                           AS tracking_since
FROM ipo_performance;

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_gmp_data_ipo_name    ON gmp_data(ipo_name);
CREATE INDEX IF NOT EXISTS idx_gmp_data_scraped_at  ON gmp_data(scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_ipo_scores_ipo_name  ON ipo_scores(ipo_name);
CREATE INDEX IF NOT EXISTS idx_ipo_scores_scored_at ON ipo_scores(scored_at DESC);
