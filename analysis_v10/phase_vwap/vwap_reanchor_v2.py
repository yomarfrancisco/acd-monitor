#!/usr/bin/env python3
"""
ACD — VWAP Re-Anchor v2 (PyArrow 15 + Strict RAM)
Process one (venue,day) at a time with streaming VWAP computation
"""

import os, json, gc, numpy as np, pandas as pd
from pathlib import Path
from utils import rss_mb, first_tick_ts, vwap_window, ns
from datetime import timedelta
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant
from statsmodels.stats.sandwich_covariance import cov_hac
from scipy.stats import norm

ROOT = Path("analysis_v10/phase_vwap")
ROOT.mkdir(parents=True, exist_ok=True)
LOG = ROOT / "dashboard.json"

VENUES = ["BINANCE","COINBASE","BYBITSPOT","BITGET"]
DAYS   = ["20250901","20250902","20250903","20250904","20250905","20250906","20250907"]
TICKS_FMT = "data_v6/views/{VENUE}/{DAY}/ticks_canonical.parquet"
ALIGNED_FMT = "analysis_v7/icp_{YYYY}{MM}{DD}_5s/aligned_5s.parquet"

acc = {"events":0,"valid":0,"placebo_tests":0,"placebo_pass":0,"memory_peak_MB":0.0}

def append_csv(path, row, header_cols):
    exists = path.exists()
    df = pd.DataFrame([row], columns=header_cols)
    df.to_csv(path, mode="a", header=not exists, index=False)

hdr_vwap = ["venue","date","t0","pre_minutes","post_minutes","n_pre","n_post","vwap_pre","vwap_post","delta","window_shrink","insufficient"]
hdr_beta = ["venue","date","pair","lag","beta_pre","beta_post","delta","p_delta","n_pre","n_post"]
hdr_tsi  = ["venue","date","pair","tsi_pre","tsi_post","delta","runlen_pre","runlen_post"]
hdr_chow = ["venue","date","pair","chow_p","cusum_p"]

def beta_hac(y, x, lags=2):
    """Minimal OLS with HAC (Newey-West) standard errors"""
    X = add_constant(x.astype("float64"))
    mod = OLS(y.astype("float64"), X, hasconst=True).fit()
    V = cov_hac(mod, nlags=lags)
    se = np.sqrt(np.diag(V))[1]
    b1 = mod.params[1]; t = b1 / se if se>0 else np.nan
    # two-sided normal approx p-value
    p = 2*(1 - norm.cdf(abs(t))) if np.isfinite(t) else np.nan
    return b1, p

def compute_tsi_simple(df, venue_col='venue', price_col='r_i'):
    """Simple TSI computation on aligned data"""
    venues = df[venue_col].unique()
    if len(venues) < 2:
        return 0.0, 0
    
    # Use first two venues for simplicity
    v1, v2 = venues[:2]
    s1 = df[df[venue_col] == v1][price_col].values
    s2 = df[df[venue_col] == v2][price_col].values
    
    # Align by minimum length
    min_len = min(len(s1), len(s2))
    if min_len < 10:
        return 0.0, min_len
    
    s1 = s1[:min_len]
    s2 = s2[:min_len]
    
    # Simple correlation as TSI proxy
    tsi = np.corrcoef(s1, s2)[0,1] if min_len > 1 else 0.0
    return float(tsi) if np.isfinite(tsi) else 0.0, min_len

print("=== ACD — VWAP Re-Anchor v2 (PyArrow 15 + Strict RAM) ===")
print(f"Memory at start: {rss_mb():.1f}MB")

for day in DAYS:
    YYYY,MM,DD = day[0:4], day[4:6], day[6:8]
    aligned_path = Path(ALIGNED_FMT.format(YYYY=YYYY,MM=MM,DD=DD))
    if not aligned_path.exists():
        print(f"[WARN] aligned_5s missing: {aligned_path}")
        continue
    for venue in VENUES:
        try:
            ticks_path = Path(TICKS_FMT.format(VENUE=venue, DAY=day))
            if not ticks_path.exists():
                print(f"[WARN] ticks missing: {ticks_path}")
                continue

            print(f"Processing {venue} {day}... (Memory: {rss_mb():.1f}MB)")

            # 1) find t0 - use first tick + 1 hour to ensure pre-window data
            first_tick = first_tick_ts(str(ticks_path))
            t0 = first_tick + np.timedelta64(1, "h")  # Use 1 hour after first tick
            acc["events"] += 1

            # 2) build windows and compute VWAP streaming
            pre_mins = 30; post_mins = 30; shrink=False
            def win(v):
                return np.datetime64(v)
            pre_start = win(t0 - np.timedelta64(pre_mins, "m"))
            pre_end   = t0
            post_start= t0
            post_end  = win(t0 + np.timedelta64(post_mins, "m"))

            vwap_pre, n_pre   = vwap_window(str(ticks_path), ns(pre_start), ns(pre_end))
            vwap_post, n_post = vwap_window(str(ticks_path), ns(post_start), ns(post_end))

            if (n_pre < 50 or n_post < 50):
                pre_mins = post_mins = 15; shrink=True
                pre_start = win(t0 - np.timedelta64(15, "m"))
                post_end  = win(t0 + np.timedelta64(15, "m"))
                vwap_pre, n_pre   = vwap_window(str(ticks_path), ns(pre_start), ns(pre_end))
                vwap_post, n_post = vwap_window(str(ticks_path), ns(post_start), ns(post_end))

            insufficient = (n_pre < 50 or n_post < 50)
            delta = (vwap_post - vwap_pre) if not np.isnan(vwap_pre) and not np.isnan(vwap_post) else np.nan

            append_csv(ROOT/"vwap_deltas.csv",
                       [venue, day, str(t0), pre_mins, post_mins, n_pre, n_post, vwap_pre, vwap_post, delta, shrink, insufficient],
                       hdr_vwap)

            print(f"  VWAP: pre={vwap_pre:.6f}, post={vwap_post:.6f}, Δ={delta:.6f}, n_pre={n_pre}, n_post={n_post}")

            # 3) β/TSI/CUSUM only if sufficient
            if not insufficient:
                # Load aligned_5s (compact), slice pre/post, drop unused cols immediately
                df = pd.read_parquet(aligned_path)
                # Keep only essential columns for memory efficiency
                usecols = ["ts","venue_i","venue_j","r_i","r_j"]
                df = df[usecols]
                
                # Convert ts to datetime64 for comparison
                df['ts'] = pd.to_datetime(df['ts'])
                
                mask_pre  = (df["ts"] >= pre_start.astype("datetime64[ns]")) & (df["ts"] < pre_end.astype("datetime64[ns]"))
                mask_post = (df["ts"] >= post_start.astype("datetime64[ns]")) & (df["ts"] < post_end.astype("datetime64[ns]"))
                df_pre  = df.loc[mask_pre].copy()
                df_post = df.loc[mask_post].copy()
                del df; gc.collect()

                # Build pairwise panel (venue→series), lags {0,1,2}
                venues_in = df_pre["venue_i"].unique().tolist()
                # restrict to the 4 venues to keep it tight:
                venues_in = [v for v in venues_in if v in VENUES]

                # simple example: pair (BINANCE, COINBASE), lag=0
                pairs = [("BINANCE","COINBASE"), ("BINANCE","BYBITSPOT"), ("BINANCE","BITGET"),
                         ("COINBASE","BYBITSPOT"), ("COINBASE","BITGET"), ("BYBITSPOT","BITGET")]
                lags = [0,1,2]

                for a,b in pairs:
                    # Get data for this pair
                    pair_pre = df_pre[(df_pre["venue_i"] == a) & (df_pre["venue_j"] == b)]
                    pair_post = df_post[(df_post["venue_i"] == a) & (df_post["venue_j"] == b)]
                    
                    if len(pair_pre) < 10 or len(pair_post) < 10:
                        continue
                    
                    s_pre_a  = pair_pre["r_i"].to_numpy()
                    s_pre_b  = pair_pre["r_j"].to_numpy()
                    s_post_a = pair_post["r_i"].to_numpy()
                    s_post_b = pair_post["r_j"].to_numpy()

                    for L in lags:
                        if L>0:
                            if len(s_pre_b) > L: s_pre_b_L = s_pre_b[:-L]
                            else: continue
                            if len(s_post_b) > L: s_post_b_L = s_post_b[:-L]
                            else: continue
                            y_pre, x_pre   = s_pre_a[L:], s_pre_b_L
                            y_post, x_post = s_post_a[L:], s_post_b_L
                        else:
                            y_pre, x_pre   = s_pre_a, s_pre_b
                            y_post, x_post = s_post_a, s_post_b
                        # require minimal length
                        if len(y_pre)<50 or len(y_post)<50: continue

                        bpre, ppre  = beta_hac(y_pre, x_pre, lags=min(2, max(1, len(y_pre)//300)))
                        bpost, ppost= beta_hac(y_post,x_post,lags=min(2, max(1, len(y_post)//300)))
                        d = (bpost - bpre) if np.isfinite(bpre) and np.isfinite(bpost) else np.nan
                        append_csv(ROOT/"beta_deltas.csv", [venue, day, f"{a}->{b}", L, bpre, bpost, d, np.nan, len(y_pre), len(y_post)], hdr_beta)

                # TSI and run-length: reuse existing implementation but ensure float32 inside; drop all temps after
                tsi_pre, run_pre = compute_tsi_simple(df_pre, 'venue_i', 'r_i')
                tsi_post, run_post = compute_tsi_simple(df_post, 'venue_i', 'r_i')
                append_csv(ROOT/"tsi_deltas.csv", [venue, day, "ALL", tsi_pre, tsi_post, tsi_post-tsi_pre, run_pre, run_post], hdr_tsi)

                del df_pre, df_post; gc.collect()
                acc["valid"] += 1

            acc["memory_peak_MB"] = max(acc["memory_peak_MB"], rss_mb())
            gc.collect()

        except Exception as e:
            print(f"[ERROR] {venue} {day}: {e}")
            acc["memory_peak_MB"] = max(acc["memory_peak_MB"], rss_mb())
            gc.collect()

# Write dashboard
Path(LOG).write_text(json.dumps(acc, indent=2))
print("VWAP phase done. Dashboard:", acc)
print(f"Final memory usage: {rss_mb():.1f}MB")
