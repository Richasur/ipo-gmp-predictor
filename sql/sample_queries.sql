-- ============================================================
-- Useful ad-hoc queries for IPO GMP Predictor
-- ============================================================

-- All current IPO signals
SELECT ipo_name, score, signal, confidence, reasons, scored_at
FROM ipo_scores_latest
ORDER BY score DESC;

-- GMP trend for a specific IPO
SELECT ipo_name, gmp_percent, prev_gmp, gmp_delta, scraped_at
FROM gmp_trend
WHERE ipo_name = 'Mehul Telecom'
ORDER BY scraped_at DESC
LIMIT 50;

-- Model performance
SELECT * FROM model_performance_summary;

-- Raw data last 24 hours
SELECT * FROM gmp_data
WHERE scraped_at > NOW() - INTERVAL '24 hours'
ORDER BY scraped_at DESC;

-- IPOs with positive GMP trend
SELECT ipo_name, gmp_percent, gmp_delta, scraped_at
FROM gmp_trend
WHERE gmp_delta > 0
ORDER BY gmp_delta DESC;

-- All STRONG BUY signals history
SELECT ipo_name, score, signal, confidence, scored_at
FROM ipo_scores
WHERE signal = 'STRONG BUY'
ORDER BY scored_at DESC;

-- Prediction accuracy per IPO
SELECT ipo_name, predicted_gain, actual_gain, abs_error, correct_direction, tracked_at
FROM ipo_performance
ORDER BY tracked_at DESC;
