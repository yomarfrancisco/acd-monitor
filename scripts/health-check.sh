#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-https://binance-proxy-broken-night-96.fly.dev}"

echo "== OKX =="
curl -s "$HOST/okx/market/candles?instId=BTC-USDT&bar=5m&limit=300" | jq -e 'select(.code=="0") | .data | length>=300' >/dev/null
curl -s "$HOST/okx/market/ticker?instId=BTC-USDT" | jq -e '.data[0] | (.bidPx|tonumber) and (.askPx|tonumber)' >/dev/null
echo "OKX: PASS"

echo "== Kraken =="
curl -s "$HOST/kraken/0/public/OHLC?pair=XBTUSD&interval=5&count=2" | jq -e '.error|length==0' >/dev/null
curl -s "$HOST/kraken/0/public/Ticker?pair=XBTUSD" | jq -e '.result|to_entries[0].value | (.b[0]|tonumber) and (.a[0]|tonumber)' >/dev/null
echo "Kraken: PASS"

echo "== Binance =="
curl -s -w "\n%{http_code}\n" "$HOST/binance/api/v3/ping" | sed -n '2p' | grep -q '^200$'
curl -s "$HOST/binance/api/v3/ticker/bookTicker?symbol=BTCUSDT" | jq -e '(.bidPrice|tonumber) and (.askPrice|tonumber)' >/dev/null
echo "Binance: PASS"

echo "== Bybit (v5 only) =="
curl -s "$HOST/bybit/v5/market/kline?category=linear&symbol=BTCUSDT&interval=5&limit=300" | jq -e '.result.list|length>=300' >/dev/null
curl -s "$HOST/bybit/v5/market/tickers?category=linear&symbol=BTCUSDT" | jq -e '.result.list[0] | (.bid1Price|tonumber) and (.ask1Price|tonumber)' >/dev/null
echo "Bybit v5: PASS"

echo "== Bybit legacy path (should be 410) =="
code=$(curl -s -o /dev/null -w "%{http_code}" "$HOST/bybit/market/tickers?category=linear&symbol=BTCUSDT")
test "$code" = "410"
echo "Bybit legacy 410: PASS"

echo "ALL CHECKS PASSED"