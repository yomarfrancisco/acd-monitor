// server.js
import express from "express";
import fetch from "node-fetch";

const app = express();
const PORT = process.env.PORT || 3000;

async function forward(res, target) {
  console.log(`[Proxy] → ${target}`);
  const r = await fetch(target, {
    headers: {
      "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
      "Accept": "application/json,text/plain,*/*",
    },
  });

  const text = await r.text();
  try {
    const json = JSON.parse(text);
    res.status(r.status).json(json);
  } catch {
    res.status(r.status).type(r.headers.get("content-type") || "text/plain").send(text);
  }
}

// Kraken
app.get("/kraken/*", async (req, res) => {
  const path = req.params[0];
  const qs = req.url.includes("?") ? req.url.slice(req.url.indexOf("?")) : "";
  const target = `https://api.kraken.com/0/public/${path}${qs}`;
  try { await forward(res, target); } catch (e) {
    console.error("[Proxy][kraken] error", e);
    res.status(502).json({ error: "kraken_proxy_error" });
  }
});

// OKX
app.get("/okx/*", async (req, res) => {
  const path = req.params[0];
  const qs = req.url.includes("?") ? req.url.slice(req.url.indexOf("?")) : "";
  const target = `https://www.okx.com/api/v5/${path}${qs}`;
  try { await forward(res, target); } catch (e) {
    console.error("[Proxy][okx] error", e);
    res.status(502).json({ error: "okx_proxy_error" });
  }
});

// Bybit
app.get("/bybit/*", async (req, res) => {
  const path = req.params[0];
  const qs = req.url.includes("?") ? req.url.slice(req.url.indexOf("?")) : "";
  const target = `https://api.bybit.com/v5/${path}${qs}`;
  try { await forward(res, target); } catch (e) {
    console.error("[Proxy][bybit] error", e);
    res.status(502).json({ error: "bybit_proxy_error" });
  }
});

app.get("/", (_req, res) => res.send("ok"));
app.listen(PORT, () => console.log(`🚀 proxy up on :${PORT}`));