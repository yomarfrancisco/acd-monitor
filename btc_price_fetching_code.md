# BTC Price Fetching Code Analysis

## 🔍 Key Lines of Code for BTC Price Fetching

### 1. **RAW DATA EXTRACTION** (from S3 Parquet files)
**File:** `create_robust_view.sql`
```sql
-- Lines 5-6: Extract price fields from raw tick data
ts_exchange, best_bid, best_ask, last_px, bid_sz, ask_sz, trade_sz,
"$path" AS _path
FROM acd_snapshots.btc_ticks_files_v2
```

### 2. **ENRICHED DATA PROCESSING**
**File:** `create_enriched_v4_fixed.sql`
```sql
-- Lines 8-10: Calculate derived price metrics
ts_exchange, best_bid, best_ask, last_px, bid_sz, ask_sz, trade_sz,
(best_bid + best_ask)/2.0                                       AS mid_px,
(best_ask - best_bid) / NULLIF((best_ask + best_bid)/2.0, 0) * 10000.0 AS spread_bps,
```

### 3. **LATEST PRICE EXTRACTION**
**File:** `create_market_last_px_v4.sql`
```sql
-- Lines 12-13: Select price fields
last_px, best_bid, best_ask
FROM acd_derived.btc_ticks_enriched_v4

-- Lines 16-20: Get most recent prices per venue
max_by(last_px, ts)  AS last_px,
max_by(best_bid, ts) AS last_bid,
max_by(best_ask, ts) AS last_ask,
MAX(ts)              AS ts
```

### 4. **PYTHON QUERY EXECUTION**
**Key Python code that was executed:**

```python
# Athena client setup
import boto3
athena = boto3.client('athena')

# Latest prices query
latest_prices_sql = '''
SELECT 
  venue,
  last_px,
  best_bid,
  best_ask,
  (best_bid + best_ask) / 2.0 AS mid_price,
  from_unixtime(
    CASE WHEN ts_exchange > 9e14 THEN ts_exchange/1000000.0
         WHEN ts_exchange > 9e11 THEN ts_exchange/1000.0
         ELSE ts_exchange*1.0 END
  ) AS timestamp
FROM acd_derived.btc_ticks_enriched_v4
WHERE ts_exchange IS NOT NULL
ORDER BY ts_exchange DESC
LIMIT 10;
'''

# Query execution
response = athena.start_query_execution(
    QueryString=latest_prices_sql,
    WorkGroup='primary',
    ResultConfiguration={
        'OutputLocation': 's3://acd-monitor-derived/athena-results/'
    }
)

# Result processing
response = athena.get_query_results(QueryExecutionId=execution_id)
rows = []
for row in response['ResultSet']['Rows']:
    row_data = [field.get('VarCharValue', '') for field in row['Data']]
    rows.append(row_data)

# Price extraction
for i, row in enumerate(rows[1:], 1):  # Skip header
    venue = row[0]
    last_px = float(row[1])
    best_bid = float(row[2])
    best_ask = float(row[3])
    mid_price = float(row[4])
    timestamp = row[5]
```

## 📊 **CRITICAL PRICE FIELDS:**

1. **`last_px`** - Last trade price (most important for current market price)
2. **`best_bid`** - Best bid price (highest buy order)
3. **`best_ask`** - Best ask price (lowest sell order)
4. **`mid_px`** - Mid price calculated as `(best_bid + best_ask) / 2.0`
5. **`spread_bps`** - Spread in basis points calculated as `(ask - bid) / mid * 10000`

## 🔄 **DATA FLOW:**

1. **S3 Parquet files** → Raw tick data with price fields
2. **Robust view** → Extract and clean price data with venue identification
3. **Enriched table** → Calculate mid prices and spreads
4. **Latest price views** → Get most recent prices per venue
5. **Python queries** → Execute SQL and process results into Python data structures

## 🎯 **FINAL RESULT:**

The system fetches BTC prices using:
- **Primary source**: `last_px` field from raw tick data
- **Derived metrics**: `mid_px` and `spread_bps` calculated from bid/ask
- **Latest prices**: `max_by()` functions to get most recent values per venue
- **Python processing**: Athena queries executed via boto3 client

