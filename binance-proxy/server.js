import express from "express";
import fetch from "node-fetch";

const app = express();
const PORT = process.env.PORT || 3000;

app.get("/binance/:endpoint", async (req, res) => {
  try {
    const { endpoint } = req.params;
    const query = req.url.split("?")[1] || "";
    const target = `https://api.binance.com/api/v3/${endpoint}${query ? "?" + query : ""}`;

    console.log(`[Proxy] Fetching: ${target}`);
    const response = await fetch(target, { headers: { "User-Agent": "binance-proxy" } });

    if (!response.ok) {
      const text = await response.text();
      return res.status(response.status).json({ error: "binance_fetch_failed", details: text });
    }

    const data = await response.json();
    res.json(data);
  } catch (err) {
    console.error("[Proxy] Error:", err);
    res.status(500).json({ error: "proxy_error", details: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`🚀 Binance proxy running on port ${PORT}`);
});
