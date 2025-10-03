CREATE OR REPLACE VIEW acd_derived.liq_1m_v4 AS
WITH ticks AS (
  SELECT
    from_unixtime(
      CASE WHEN ts_exchange > 9e14 THEN ts_exchange/1000000.0
           WHEN ts_exchange > 9e11 THEN ts_exchange/1000.0
           ELSE ts_exchange*1.0 END
    ) AS ts,
    venue,
    last_px AS price,
    trade_sz AS vol,
    best_bid, best_ask, bid_sz, ask_sz
  FROM acd_derived.btc_ticks_enriched_v4
  WHERE ts_exchange IS NOT NULL
),
bucketed AS (
  SELECT
    from_unixtime(60 * floor(to_unixtime(ts)/60)) AS bucket_1m,
    venue,
    price, vol, best_bid, best_ask, bid_sz, ask_sz, ts
  FROM ticks
)
SELECT
  bucket_1m,
  venue,
  -- VWAP within the minute
  sum(price * vol) / NULLIF(sum(vol), 0)                        AS vwap,
  -- Mid at open/close (optional)
  min_by((best_bid+best_ask)/2.0, ts)                           AS mid_open,
  max_by((best_bid+best_ask)/2.0, ts)                           AS mid_close,
  -- Quoted spread (bps) averaged within the minute
  avg( (best_ask - best_bid) / NULLIF((best_ask+best_bid)/2.0,0) * 10000.0 ) AS spread_bps_mean,
  -- Top-of-book imbalance proxy
  avg( (ask_sz - bid_sz) / NULLIF(ask_sz + bid_sz, 0) )         AS tob_imbalance_mean,
  sum(vol)                                                      AS volume
FROM bucketed
GROUP BY 1,2;
