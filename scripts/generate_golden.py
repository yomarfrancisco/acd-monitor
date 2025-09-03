#!/usr/bin/env python3
# Generates deterministic golden CSVs for CI (no external deps beyond pandas/numpy)
import hashlib
import json
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)


def row_hash(d):
    raw = json.dumps(d, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


def gen_competitive():
    # Two environments with different sensitivities; decorrelated noise
    dates = pd.date_range("2024-01-01", periods=120, freq="D", tz="UTC")
    env = np.where(dates < "2024-02-15", 0, 1)
    base_fnb, base_ned = 140, 150
    shock = (env * 15.0) + rng.normal(0, 2, len(dates))  # environment shock
    fnb = base_fnb + 0.7 * shock + rng.normal(0, 3, len(dates))
    ned = base_ned + 0.3 * shock + rng.normal(0, 3, len(dates))
    rows = []
    for ts, pf, pn in zip(dates, fnb, ned):
        for firm, price in (("FNB", pf), ("NED", pn)):
            d = dict(
                ts=ts.isoformat(),
                firm_id=firm,
                price=round(float(price), 1),
                unit="bps",
                src="derived",
                confidence=95,
            )
            d["hash"] = row_hash(d)
            rows.append(d)
    pd.DataFrame(rows).to_csv("data/golden/synthetic_competitive.csv", index=False)


def gen_coordinated():
    # Stable linear relationship across environments (invariance)
    dates = pd.date_range("2024-01-01", periods=120, freq="D", tz="UTC")
    base = 151 + np.sin(np.linspace(0, 2 * np.pi, len(dates))) * 0.8
    eps = rng.normal(0, 0.6, len(dates))
    fnb = base + eps
    ned = base + 2.5 + eps * 0.2
    rows = []
    for ts, pf, pn in zip(dates, fnb, ned):
        for firm, price in (("FNB", pf), ("NED", pn)):
            d = dict(
                ts=ts.isoformat(),
                firm_id=firm,
                price=round(float(price), 1),
                unit="bps",
                src="derived",
                confidence=96,
            )
            d["hash"] = row_hash(d)
            rows.append(d)
    pd.DataFrame(rows).to_csv("data/golden/synthetic_coordinated.csv", index=False)


def gen_public_like():
    dates = pd.to_datetime(["2024-06-03T10:00:00Z", "2024-06-03T12:00:00Z", "2024-06-03T14:00:00Z"])
    prices = {"FNB": [168, 169, 170], "NED": [172, 171, 172]}
    rows = []
    for ts in dates:
        for firm in ("FNB", "NED"):
            src = "jse" if ts.hour == 10 else "derived"
            conf = 80 if src == "jse" else 70
            d = dict(
                ts=ts.isoformat(),
                firm_id=firm,
                price=int(prices[firm][(ts.hour - 10) // 2]),
                unit="bps",
                src=src,
                confidence=conf,
            )
            d["hash"] = row_hash(d)
            rows.append(d)
    pd.DataFrame(rows).to_csv("data/golden/sample_sa_cds_public.csv", index=False)


if __name__ == "__main__":
    gen_competitive()
    gen_coordinated()
    gen_public_like()
    print("Golden datasets written to data/golden/")
