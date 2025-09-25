// server.js
import express from "express";
import fetch from "node-fetch";

const app = express();
const PORT = process.env.PORT || 3000;

// BEFORE generic passthrough - deprecate legacy Bybit paths
app.all('/bybit/market/*', (req, res) => {
  res.status(410).json({
    venue: 'bybit',
    error: 'deprecated_path',
    message: 'Use /bybit/v5/market/*'
  });
});

app.use('/:venue/*', async (req, res) => {
  const { venue } = req.params;            // e.g. "kraken"
  const rest = req.params[0] || '';        // preserves full path, e.g. "0/public/OHLC"
  const qs = req.url.includes('?') ? req.url.slice(req.url.indexOf('?')) : '';

  const upstream = {
    kraken: 'https://api.kraken.com/',     // trailing slash important
    okx:    'https://www.okx.com/api/v5/',
    bybit:  'https://api.bybit.com/',
    binance:'https://api.binance.com/',    // add if we want Binance proxied too
    coinbase:'https://api.exchange.coinbase.com/'
  }[venue];

  if (!upstream) {
    return res.status(400).json({ error: "unknown_venue", venue });
  }

  const url = upstream + rest + qs;
  console.log(`[proxy] venue=`, venue, `→`, upstream, ` path=`, req.url);

  try {
    const r = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json,text/plain,*/*'
      }
    });

    const ct = r.headers.get('content-type') || '';
    res.status(r.status);
    if (ct.includes('json')) {
      const body = await r.json();
      res.setHeader('content-type', ct);
      return res.send(body);
    } else {
      const body = await r.text();
      res.setHeader('content-type', ct || 'text/plain');
      return res.send(body);
    }
  } catch (e) {
    console.error(`[Proxy][${venue}] error`, e);
    res.status(502).json({ error: `${venue}_proxy_error`, details: String(e) });
  }
});

app.get("/", (_req, res) => res.send("ok"));
app.listen(PORT, () => console.log(`🚀 proxy up on :${PORT}`));