import gc, psutil, numpy as np, pyarrow.dataset as ds, pyarrow.parquet as pq
from datetime import timedelta

def rss_mb():
    return psutil.Process().memory_info().rss / (1024*1024)

def first_tick_ts(parquet_path:str) -> np.datetime64:
    # robust: try scanner.head(1); fallback to to_table().slice(0,1)
    d = ds.dataset(parquet_path, format="parquet")
    try:
        s = d.scanner(columns=["ts"])
        tbl = s.head(1)  # returns a Table in pa>=14
    except Exception:
        tbl = d.to_table(columns=["ts"]).slice(0,1)
    if tbl.num_rows == 0:
        raise RuntimeError(f"No rows in {parquet_path}")
    return np.datetime64(tbl.column("ts")[0].as_py(), "ns")

def vwap_window(parquet_path:str, start_ns:int, end_ns:int):
    # Stream batches, no pandas
    d = ds.dataset(parquet_path, format="parquet")
    filt = (ds.field("ts") >= np.datetime64(start_ns, "ns")) & (ds.field("ts") < np.datetime64(end_ns, "ns"))
    s = d.scanner(columns=["price","size"], filter=filt, batch_size=32768)
    num = 0.0; den = 0.0; n=0
    for b in s.to_batches():
        p = b.column(0).to_numpy()    # price float64
        q = b.column(1).to_numpy()    # size  float64
        num += float(np.dot(p, q))
        den += float(np.sum(q))
        n   += len(p)
    return (num/den if den>0 else np.nan), n

def ns(dt64: np.datetime64) -> int:
    return int(dt64.astype("datetime64[ns]").astype(np.int64))





