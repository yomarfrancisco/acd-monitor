# Download Method v2.0

## API Configuration
- **LIST URL**: `https://s3.flatfiles.coinapi.io/bucket/?prefix=T-TRADES/...`
- **GET URL**: `https://s3.flatfiles.coinapi.io/coinapi/{key}`
- **Header**: `X-CoinAPI-Key: <REDACTED>`
- **User-Agent**: `ACD-Monitor/1.0`
- **TLS**: `verify=True`

## XML Parsing
- **Namespace**: No namespace
- **Elements**: `Contents` → `Key`
- **Truncation**: Handle `IsTruncated=false`

## Budget Control
- **Total calls**: ≤160 calls
- **Retries**: 3 retries (30s/60s/120s + jitter)
- **Concurrency**: 2 workers

## Write Policy
- **Atomic writes**: `.part` → `fsync` → `rename`
- **No-clobber**: Fail on exists
- **Output pathing**: `<root>/<week_tag>/<date>/E-<VENUE>/<PAIR>.csv.gz` (unique per day)

## Post-Write Checks
- **Content-Length**: > 0
- **Gzip header**: OK
- **SHA-256**: Computed and logged

## Local Logs
- **Run log**: `<run_id>/runlog.txt`
- **Manifest**: `manifest.csv`
- **Spend**: `spend.json`

## Prohibited Behavior
- No flat writes
- No overwrites
- No silent dedupe

## Version
- **Version**: 2.0
- **Created**: 2025-10-11T14:45:00Z