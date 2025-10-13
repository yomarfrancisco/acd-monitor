# Phase 39F Pre-Flight Download Plan

## Targets
1. **Week -6 (2025-07-14…07-20)**: BTCUSD-class for {BINANCE, COINBASE, BYBITSPOT, BITGET}
2. **Week -7 (2025-07-07…07-13)**: COINBASE BTC-USD only

## Endpoints & URLs
- **LIST URL Template**: `https://s3.flatfiles.coinapi.io/bucket/?prefix=T-TRADES/D-YYYYMMDD/E-<VENUE>/`
- **GET URL Template**: `https://s3.flatfiles.coinapi.io/coinapi/{Key}`
- **Headers**: `X-CoinAPI-Key: 7f036b38-38d6-4ed6-9fce-00a06280a0f6`, `User-Agent: ACD-Monitor/1.0`

## Filename Filter
Case-insensitive regex: `/(^|[^\w])(BTCUSDT|BTC-USD|BTCUSD)([^\w]|$)/`
- Includes COINBASE format: `BTC__002DUSD`

## Planned Call Budget
- **LIST pass**: Week -6 → 7×4=28; Week -7 Coinbase → 7; **Total LIST ≤ 35**
- **GET cap** (after LIST reveals keys): **≤ 85**
- **Global hard cap** (LIST+GET) for 39F: **≤ 120 calls**

## Abort Rules
- If a day/venue returns zero keys twice, mark DAY-MISSING and skip GETs for that slot
- If API budget exceeded, stop immediately
- If memory > 1.0 GB, abort

## Exit Gates (must meet or we stop)
1. **Week -7 COINBASE BTC-USD**: present on ≥5/7 days
2. **Week -6 BTCUSD-class**: present on ≥5/7 days for ≥2 venues OR ≥20/28 total day-venue slots filled across venues
3. **Quality**: No duplicates; zero zero-byte files

## Expected Outcomes
- Week -6: 4 venues × 7 days = 28 potential slots
- Week -7: 1 venue × 7 days = 7 potential slots
- Target success rate: ≥70% of potential slots

## Risk Mitigation
- Exponential backoff: 30s → 60s → 120s
- Max 2 parallel downloads
- Timeout per request: 120s
- Retry on 403/429/5xx errors only
