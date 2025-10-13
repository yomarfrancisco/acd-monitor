#!/usr/bin/env python3
import os, json, boto3, pandas as pd
import numpy as np

BUCKET = os.getenv("ACD_S3_BUCKET", "acd-monitor-snapshots")
PREFIX = os.getenv("ACD_S3_PREFIX", "snapshots")
SYMBOLS = os.getenv("SYMBOLS", "BTC-USD,ETH-USD").split(",")
VENUES = os.getenv("VENUES", "binance coinbase kraken okx bybit").split()

s3 = boto3.client("s3")


def list_latest(sym):
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=f"{PREFIX}/{sym}/")
    keys = [o["Key"] for o in resp.get("Contents", []) if o["Key"].endswith("OVERLAP.json")]
    if not keys:
        return None
    keys.sort()
    base = keys[-1].rsplit("/", 1)[0]
    return base


def check_window(base):
    out = {"base": base, "venues": {}}
    for v in VENUES:
        # pick first parquet
        resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=f"{base}/ticks/{v}/")
        p = [o["Key"] for o in resp.get("Contents", []) if o["Key"].endswith(".parquet")]
        if not p:
            out["venues"][v] = {"present": False}
            continue
        key = p[0]
        uri = f"s3://{BUCKET}/{key}"
        try:
            df = pd.read_parquet(uri, storage_options={"anon": False})
            cols = set(df.columns)
            ts_valid = "ts_exchange" in cols
            dup_ts = int(df["ts_exchange"].duplicated().sum()) if ts_valid else None
            out["venues"][v] = {
                "present": True,
                "rows": int(len(df)),
                "dup_ts": dup_ts,
                "cols": sorted(cols)[:20],
            }
        except Exception as e:
            out["venues"][v] = {"present": True, "error": str(e)}
    return out


def main():
    res = []
    for sym in SYMBOLS:
        base = list_latest(sym)
        if not base:
            continue
        res.append(check_window(base))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
