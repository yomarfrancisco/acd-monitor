// server.js
import express from "express";
import fetch from "node-fetch";

const app = express();
const PORT = process.env.PORT || 3000;

// Map :exchange -> base URL and path prefix builder
const UPSTREAMS = {
  binance: (endpoint, q) =>
    `https://api.binance.com/api/v3/${endpoint}${q ? "?" + q : ""}`,

  okx: (endpoint, q) =>
    // OKX public market data
    `https://www.okx.com/api/v5/market/${endpoint}${q ? "?" + q : ""}`,

  kraken: (endpoint, q) =>
    // Kraken public API (note: endpoints differ)
    // We'll pass endpoint like "OHLC" and add query as-is.
    `https://api.kraken.com/0/public/${endpoint}${q ? "?" + q : ""}`,

  bybit: (endpoint, q) =>
    // Bybit v5 public market data
    `https://api.bybit.com/v5/market/${endpoint}${q ? "?" + q : ""}`,
};

// Simple health
app.get("/healthz", (_, res) => res.status(200).json({ ok: true }));

// Generic proxy: /:exchange/:endpoint?query
app.get("/:exchange/:endpoint", async (req, res) => {
  try {
    const { exchange, endpoint } = req.params;
    const query = req.url.split("?")[1] || "";
    const builder = UPSTREAMS[exchange];
    if (!builder) return res.status(400).json({ error: "unknown_exchange" });

    const target = builder(endpoint, query);
    console.log(`[Proxy] ${exchange} → ${target}`);

    const upstream = await fetch(target, { headers: { Accept: "application/json" } });
    const text = await upstream.text();

    // 451/geo or non-OK: bubble status with details
    if (!upstream.ok) {
      return res.status(upstream.status).json({
        error: `${exchange}_fetch_failed`,
        details: text.slice(0, 2_000),
      });
    }

    // Try return raw JSON; if not JSON, forward text
    try {
      const json = JSON.parse(text);
      return res.json(json);
    } catch {
      return res
        .status(502)
        .json({ error: "upstream_non_json", details: text.slice(0, 2_000) });
    }
  } catch (err) {
    console.error("[Proxy] Error:", err);
    res.status(500).json({ error: "proxy_error", details: String(err?.message || err) });
  }
});

app.listen(PORT, () => console.log(`🚀 multi-exchange proxy on :${PORT}`));