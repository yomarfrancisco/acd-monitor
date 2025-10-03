# 🔒 DASHBOARD QUERY GUARDS - IMPLEMENTATION TEMPLATE

## 📊 A2. Dashboard Query Guards:

### ✅ RECOMMENDED TEMPLATE:
```sql
-- All "latest" queries should include both gates:
SELECT venue, last_px, ts_verified
FROM acd_derived.market_last_px_v5
WHERE sanity_price_ok = 1
  AND ts_verified > now() - interval '5' minute
ORDER BY ts_verified DESC;
```

### ✅ FALLBACK FOR FAILED CHECKS:
```sql
-- If either freshness or sanity fails:
SELECT 'data stale or failed sanity' AS status
WHERE NOT EXISTS (
  SELECT 1 FROM acd_derived.market_last_px_v5
  WHERE sanity_price_ok = 1
    AND ts_verified > now() - interval '5' minute
);
```

### ✅ ADDITIONAL SANITY CHECKS:
```sql
-- Additional price sanity for 2025+ dates:
AND (
  date_format(ts_verified, '%Y') < '2025'
  OR last_px > 80000
)
```

## 🚨 IMPLEMENTATION STATUS:
- **A1. Writer Pause**: ⚠️ MANUAL ACTION REQUIRED (requires writer system access)
- **A2. Dashboard Guards**: ✅ TEMPLATE PROVIDED (ready for implementation)
