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
  const { venue } = req.params;

  const upstream = {
    kraken:  'https://api.kraken.com/',
    okx:     'https://www.okx.com/api/v5/',
    bybit:   'https://api.bybit.com/',
    binance: 'https://api.binance.com/',
    coinbase: 'https://api.exchange.coinbase.com/', // Exchange v2
  }[venue];

  if (!upstream) return res.status(400).json({ error: 'Unknown venue' });

  // strip "/{venue}" and forward the rest
  const pathAfterVenue = req.originalUrl.replace(`/${venue}`, '');
  const url = upstream.replace(/\/+$/,'') + pathAfterVenue;

  console.log('[proxy] venue=%s path=%s qs=%s', venue, req.path, req.originalUrl.split('?')[1]||'');

  try {
    const r = await fetch(url, { headers: { 'Accept': 'application/json' }});
    const body = await r.text();
    res.status(r.status).set('content-type', r.headers.get('content-type') || 'application/json').send(body);
  } catch (e) {
    console.error(`[Proxy][${venue}] error`, e);
    res.status(502).json({ error: `${venue}_proxy_error`, details: String(e) });
  }
});

app.get("/", (_req, res) => res.send("ok"));
app.listen(PORT, () => console.log(`🚀 proxy up on :${PORT}`));