#!/usr/bin/env python3
"""
CI Audit Parquet Head Script
"""

import json
import os
import sys

import pyarrow.fs as fs
import pyarrow.parquet as pq


def main():
    bucket = os.environ["S3_BUCKET"]
    candidate_prefix = "snapshots/BTC-USD"
    s3 = fs.S3FileSystem()
    files = []

    for de in s3.get_file_info(fs.FileSelector(f"{bucket}/{candidate_prefix}", recursive=True)):
        if de.type == fs.FileType.File and de.path.endswith(".parquet"):
            files.append(de.path)
            if len(files) >= 10:
                break

    out = {"tested_files": files, "sample": None, "error": None}

    try:
        if files:
            table = pq.read_table(f"s3://{files[0]}", filesystem=s3, columns=None)
            df = table.to_pandas().head(5)
            out["sample"] = {
                "columns": list(df.columns),
                "rows": df.astype(object).where(df.notna(), None).to_dict(orient="records"),
            }
        else:
            out["error"] = "No parquet files found under prefix."
    except Exception as e:
        out["error"] = str(e)

    if len(sys.argv) > 1:
        output_file = sys.argv[1]
        with open(output_file, "w") as f:
            json.dump(out, f, indent=2)
    else:
        print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
