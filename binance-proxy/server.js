// server.js
import express from "express";
import fetch from "node-fetch";

const app = express();
const PORT = process.env.PORT || 3000;

// Catch any nested path under /binance/*
app.get("/binance/*", async (req, res) => {
  try {
    // Everything after /binance/
    const path = req.path.replace(/^\/binance\//, ""); // e.g. 'ticker/bookTicker' or 'klines'
    const query = req.url.includes("?") ? req.url.split("?")[1] : "";
    const target = `https://api.binance.com/api/v3/${path}${query ? "?" + query : ""}`;

    console.log(`[Proxy] GET → ${target}`);

    const response = await fetch(target, {
      headers: { "User-Agent": "acd-monitor-proxy/1.0 (+https://example.com)" }
    });

    const text = await response.text();

    if (!response.ok) {
      return res.status(response.status).json({
        error: "binance_fetch_failed",
        details: text
      });
    }

    // Try parse JSON, otherwise forward raw text as JSON content-type
    try {
      const json = JSON.parse(text);
      return res.json(json);
    } catch {
      res.type("application/json").send(text);
    }
  } catch (err) {
    console.error("[Proxy] Error:", err);
    res.status(500).json({ error: "proxy_error", details: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`🚀 Binance proxy running on port ${PORT}`);
});
