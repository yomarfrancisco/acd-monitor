CREATE OR REPLACE VIEW acd_derived.env_flags_1m_v4 AS
WITH t AS (
  SELECT
    from_unixtime(60 * floor(to_unixtime(
      from_unixtime(
        CASE WHEN ts_exchange > 9e14 THEN ts_exchange/1000000.0
             WHEN ts_exchange > 9e11 THEN ts_exchange/1000.0
             ELSE ts_exchange*1.0 END
      )
    )/60)) AS ts_min
  FROM acd_derived.btc_ticks_enriched_v4
)
SELECT
  ts_min,
  CASE
    WHEN date_format(ts_min, '%H:%i:%s') BETWEEN '13:30:00' AND '20:00:00' THEN 1
    ELSE 0
  END AS is_ny_open
FROM (SELECT DISTINCT ts_min FROM t);

