// server.js
import express from "express";
import fetch from "node-fetch";
import cors from "cors";

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());

// Catch-all for any nested v3 path, e.g. /binance/ticker/bookTicker
app.get("/binance/*", async (req, res) => {
  try {
    // subpath after /binance/
    const subpath = req.originalUrl.replace(/^\/binance\//, ""); // e.g. "ticker/bookTicker?symbol=BTCUSDT"
    // Ensure it targets Binance v3
    const target = `https://api.binance.com/api/v3/${subpath}`;

    console.log(`[Proxy] GET → ${target}`);
    const response = await fetch(target, {
      // forward minimal headers; Binance ignores most, but keep UA
      headers: { "User-Agent": "acd-monitor-proxy/1.0" },
    });

    const ctype = response.headers.get("content-type") || "";
    const text = await response.text();

    if (!response.ok) {
      console.error(`[Proxy] Upstream ${response.status} ${ctype} :: ${text.slice(0, 200)}`);
      return res.status(response.status).json({
        error: "binance_fetch_failed",
        status: response.status,
        details: text,
      });
    }

    // Binance returns application/json; pass it through. If not JSON, still return as JSON when possible.
    if (ctype.includes("application/json")) {
      res.setHeader("content-type", "application/json; charset=utf-8");
      return res.status(200).send(text); // already JSON string
    }

    // Fallback: try parse as JSON; otherwise wrap as string
    try {
      const maybe = JSON.parse(text);
      return res.status(200).json(maybe);
    } catch {
      return res.status(200).json({ raw: text });
    }
  } catch (err) {
    console.error("[Proxy] Error:", err);
    return res.status(500).json({ error: "proxy_error", details: String(err?.message || err) });
  }
});

app.listen(PORT, () => {
  console.log(`🚀 Binance proxy running on port ${PORT}`);
});
