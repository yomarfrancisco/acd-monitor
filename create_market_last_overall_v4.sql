CREATE OR REPLACE VIEW acd_derived.market_last_overall_v4 AS
SELECT *
FROM acd_derived.market_last_px_v4
ORDER BY ts DESC
LIMIT 1;

