import sys, json, os, io
import pandas as pd
import boto3

BUCKET = os.environ.get("ACD_S3_BUCKET", "acd-monitor-snapshots")
PREFIX = os.environ["WAVE1_PREFIX"]  # e.g. analysis/20251001/wave1
SYMBOLS = ["btc_usd","eth_usd"]
ARTS = ["variance_ratios","autocorr","xcorr","rolling","pca"]  # pca optional

s3 = boto3.client("s3")
results = {"checks":[], "status":"ok"}

def read_parquet_s3(key):
    bio = io.BytesIO(s3.get_object(Bucket=BUCKET, Key=key)["Body"].read())
    return pd.read_parquet(bio)

def exists(key):
    try:
        s3.head_object(Bucket=BUCKET, Key=key); return True
    except Exception: return False

def require(cond, msg):
    if not cond:
        results["checks"].append({"ok":False,"msg":msg})
        results["status"] = "fail"

def notice(msg):
    results["checks"].append({"ok":True,"msg":msg})

for sym in SYMBOLS:
    base = f"{PREFIX}/{sym}"
    # per-artifact presence (pca is optional)
    expected = {a:f"{base}/{a}.parquet" for a in ARTS}
    for a,k in expected.items():
        if a == "pca":
            if exists(k): notice(f"{sym}/{a}: present")
            else: notice(f"{sym}/{a}: absent (treated as optional)")
        else:
            require(exists(k), f"{sym}/{a}: missing required artifact")

    # schema checks
    def check_cols(df, need, label):
        missing = [c for c in need if c not in df.columns]
        require(not missing, f"{sym}/{label}: missing cols {missing}")

    # variance_ratios & autocorr & rolling → single-venue
    for a in ["variance_ratios","autocorr","rolling"]:
        k = expected[a]
        if not exists(k): continue
        df = read_parquet_s3(k)
        check_cols(df, ["symbol","venue"], f"{a}")
        require(len(df)>0, f"{sym}/{a}: empty dataframe")

    # xcorr → pairwise venues
    kx = expected["xcorr"]
    if exists(kx):
        dfx = read_parquet_s3(kx)
        check_cols(dfx, ["symbol","venue1","venue2","cross_corr"], "xcorr")
        require(len(dfx)>0, f"{sym}/xcorr: empty dataframe")

    # PCA (optional)
    kp = expected["pca"]
    if exists(kp):
        dfp = read_parquet_s3(kp)
        # minimal sanity if present
        need_any = [c for c in ["explained_var_ratio","n_components","n_obs"] if c in dfp.columns]
        require(len(need_any)>0, f"{sym}/pca: missing expected metrics")

# write summary for artifact upload
os.makedirs("artifacts_wave1_ci", exist_ok=True)
with open("artifacts_wave1_ci/summary.json","w") as f: json.dump(results,f,indent=2)
print(json.dumps(results, indent=2))
sys.exit(0 if results["status"]=="ok" else 1)

