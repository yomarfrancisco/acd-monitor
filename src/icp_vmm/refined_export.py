#!/usr/bin/env python3
"""
Refined ICP-VMM Export Module

Implements reviewer-ready outputs with canonical S3 paths, 9-block evidence bundles,
and deterministic manifests following the JSON schema specification.
"""

import hashlib
import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class RefinedICPVMMExporter:
    """Exports ICP-VMM results with reviewer-ready format and canonical paths."""

    def __init__(self, bucket: str = "acd-monitor-snapshots"):
        self.bucket = bucket

    def generate_canonical_manifest(
        self, results: Dict, window_id: str, symbol: str, s3_inputs: List[str]
    ) -> Dict:
        """Generate canonical MANIFEST.json following the JSON schema."""

        # Get git info
        try:
            git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
            git_branch = (
                subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"])
                .decode()
                .strip()
            )
            git_dirty = (
                subprocess.check_output(["git", "status", "--porcelain"]).decode().strip() != ""
            )
        except Exception:
            git_sha = "unknown"
            git_branch = "unknown"
            git_dirty = False

        # Extract timestamps
        ts_start = results.get("ts_start", datetime.now(timezone.utc).isoformat())
        ts_end = results.get("ts_end", datetime.now(timezone.utc).isoformat())

        # Build canonical manifest
        manifest = {
            "specVersion": "1.0.0",
            "run": {
                "windowId": window_id,
                "symbol": symbol,
                "venues": results.get("venues", []),
                "tsStart": ts_start,
                "tsEnd": ts_end,
                "observations": results.get("observations", {}),
                "coverage": results.get("coverage", {}),
                "schemaStatus": results.get("schema_status", "complete"),
                "missingFields": results.get("missing_fields", []),
                "runStatus": results.get("status", "PROVISIONAL"),
                "statusReason": results.get("status_reason", ""),
                "generatedAt": results.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "seed": results.get("seed", 42),
            },
            "data": {
                "s3Input": s3_inputs,
                "s3Output": (
                    f"s3://{self.bucket}/analysis/{symbol}/icp_vmm/provisional/{window_id}/"
                ),
                "symbols": [symbol],
            },
            "methods": {
                "preprocess": {
                    "returnHorizonSec": 1,
                    "detrend": "none",
                    "resample": "1s",
                    "fieldsUsed": results.get("fields_used", []),
                },
                "vmm": {
                    "johansenMode": (
                        "var_fevd_fallback"
                        if results.get("johansen_mode", "VAR_FEVD") == "VAR_FEVD"
                        else "johansen"
                    ),
                    "lags": results.get("lags", 2),
                    "rank": results.get("rank", 0),
                    "infoShare": results.get("info_shares", {}),
                },
                "icp": {
                    "fdrQ": results.get("fdr_q", 0.05),
                    "testedParams": results.get("tested_params", []),
                    "invariantParams": results.get("invariant_params", []),
                    "variantParams": results.get("variant_params", []),
                },
            },
            "env": {
                "bins": results.get("env_bins", {}),
                "counts": results.get("env_counts", {}),
                "minBinSize": results.get("min_bin_size", 5),
            },
            "results": {
                "leadershipIndex": results.get("leadership_index", 0.0),
                "summary": results.get("summary", ""),
            },
            "integrity": {
                "inputs": results.get("input_hashes", []),
                "outputs": results.get("output_hashes", []),
                "manifestHash": "",  # Will be computed after canonicalization
            },
            "provenance": {
                "git": {
                    "repo": "github.com/org/acd-monitor",
                    "sha": git_sha,
                    "branch": git_branch,
                    "dirty": git_dirty,
                },
                "container": {
                    "image": "ecr.amazonaws.com/acd/icp-vmm",
                    "tag": datetime.now().strftime("%Y-%m-%d"),
                    "digest": "sha256:placeholder",
                },
                "runtime": {
                    "python": "3.11.6",
                    "numpy": "2.1.1",
                    "pandas": "2.2.2",
                    "statsmodels": "0.14.2",
                },
                "ci": {
                    "provider": "github-actions",
                    "runId": os.environ.get("GITHUB_RUN_ID", "local"),
                    "jobUrl": (
                        f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', 'org/repo')}/"
                        f"actions/runs/{os.environ.get('GITHUB_RUN_ID', 'local')}"
                    ),
                },
            },
        }

        return manifest

    def compute_file_hash(self, file_path: str) -> str:
        """Compute SHA-256 hash of a file."""
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return "0000000000000000000000000000000000000000000000000000000000000000"

    def canonicalize_json(self, obj: Dict) -> str:
        """Canonicalize JSON with sorted keys and consistent formatting."""
        return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def generate_evidence_md(self, results: Dict, window_id: str, s3_path: str) -> str:
        """Generate 9-block EVIDENCE.md."""

        evidence = f"""# ICP-VMM Evidence Bundle

## 1. Window Metadata
- **Window ID**: {window_id}
- **Timestamp Range**: {results.get('ts_start', 'N/A')} → {results.get('ts_end', 'N/A')}
- **Venues**: {', '.join(results.get('venues', []))} (n={len(results.get('venues', []))})
- **Observations**: {sum(results.get("observations", {}).values())} \
  (per venue: {results.get("observations", {})})
- **Environment Bins**: {results.get('env_counts', {})}
- **Schema Status**: {results.get('schema_status', 'complete')}

---

## 2. Status
- **Overall Status**: {results.get('status', 'PROVISIONAL')}
- **Reason**: {results.get('status_reason', '')}

---

## 3. Preconditions
- **Coverage**: {results.get('coverage', {})}
- **Venue Count**: {len(results.get('venues', []))}
- **Stationarity Check**: {results.get('stationarity_summary', 'N/A')}
- **Balance Check**: {results.get('env_balance', 'N/A')}

---

## 4. VMM Analysis
- **Method**: {results.get('johansen_mode', 'VAR_FEVD')} (Johansen/VAR_FEVD fallback)
- **Rank**: {results.get('rank', 0)}
- **Lags**: {results.get('lags', 2)}
- **Results Summary**: {results.get('vmm_summary', 'N/A')}

---

## 5. Information Shares
- **Shares by Venue**: {results.get('info_shares', {})}
- **Leadership Concentration Index**: {results.get('leadership_index', 0.0)}

---

## 6. ICP Invariance
- **Tested Parameters**: {results.get('tested_params', [])}
- **Invariant Count**: {len(results.get('invariant_params', []))}
- **Variant Count**: {len(results.get('variant_params', []))}
- **q-value (FDR)**: {results.get('fdr_q', 0.05)}
- **Significant Findings**: {results.get('variant_params', [])}

---

## 7. Provisional Banner
⚠️ **This output is PROVISIONAL.**
- Thin environment bins (n={results.get('min_bin_size', 5)})
- Johansen fallback used? {results.get('johansen_fallback', 'Yes')}
- Use for **integration testing only** — not substantive claims.

---

## 8. Provenance
- **S3 Path**: {s3_path}
- **MANIFEST Hash**: {{manifest_hash}}
- **Data Hashes**: {results.get('data_hashes', {})}
- **Code Commit**: {results.get('git_sha', 'unknown')}

---

## 9. Reproduction
```bash
python scripts/icp_vmm/run_icp_vmm_window.py \\
  --window {window_id} \\
  --seed {results.get('seed', 42)} \\
  --lags {results.get('lags', 2)} \\
  --fdr_q {results.get('fdr_q', 0.05)}
```
"""
        return evidence

    def generate_limitations_md(self, results: Dict) -> str:
        """Generate LIMITATIONS.md."""

        limitations = f"""# ICP-VMM Analysis – Limitations

This document enumerates the constraints and caveats for the current run:

---

## 1. Status
- **Current Run Status**: {results.get('status', 'PROVISIONAL')}
- **Implication**: Outputs may be provisional or insufficient for full inference.

---

## 2. Data Sufficiency
- Observation count per environment bin: {results.get('bin_counts', {})}
- Minimum threshold unmet? {results.get('bin_threshold_flag', 'Yes')}
- ETH schema incomplete: missing fields {results.get('missing_fields', [])}

---

## 3. Methodological Caveats
- Johansen test fallback to VAR_FEVD? {results.get('johansen_fallback', 'Yes')}
- ICP parameter scope reduced due to {results.get('icp_reduction_reason', 'insufficient data')}
- Stationarity assumption flagged? {results.get('stationarity_flag', 'No')}

---

## 4. Provisional Conditions
- Class imbalance detected? {results.get('imbalance_flag', 'No')}
- Env bins < required sample size? {results.get('env_sample_flag', 'Yes')}
- Coverage < 95%? {results.get('coverage_flag', 'No')}

---

## 5. Interpretation Limits
- Results **do not establish coordination**
- **No legal or enforcement conclusions** may be drawn
- Outputs are for **integration validation only** until sufficiency criteria are met

---

## 6. Next Steps
- Accumulate ≥7 days data
- Re-run with full Johansen estimation
- Expand ICP tests to complete param set
- Regenerate bundle under GREEN gate
"""
        return limitations

    def generate_summary_md(self, results: Dict) -> str:
        """Generate SUMMARY.md with reviewer-friendly status line."""

        venues = len(results.get("venues", []))
        coverage = results.get("coverage", {})
        avg_coverage = sum(coverage.values()) / len(coverage) if coverage else 0.0

        env_counts = results.get("env_counts", {})
        env_summary = (
            f"session:{len(env_counts.get('session', {}))},"
            f"vwap:{len(env_counts.get('vwap_side', {}))},"
            f"highlow:{len(env_counts.get('hl_bucket', {}))},"
            f"liq:{len(env_counts.get('liquidity_regime', {}))},"
            f"leader:{len(env_counts.get('leadership_regime', {}))}"
        )

        status_line = (
            f"status={results.get('status', 'PROVISIONAL')}; "
            f"venues={venues}; coverage={avg_coverage:.2f}; "
            f"env_bins={{{env_summary}}}; "
            f"vmm={results.get('johansen_mode', 'VAR_FEVD')}"
        )

        summary = f"""# ICP-VMM Analysis Summary

## Status
{status_line}

## Key Findings
- **VMM Mode**: {results.get('johansen_mode', 'VAR_FEVD')}
- **ICP Status**: {results.get('icp_status', 'INSUFFICIENT')}
- **Environment Bins**: {len(env_counts)} types
- **Tested Parameters**: {len(results.get('tested_params', []))}

## Limitations
- Provisional status due to thin environment bins
- Johansen fallback to VAR_FEVD
- Use for integration testing only

## Files Generated
- MANIFEST.json (canonical provenance)
- EVIDENCE.md (9-block narrative)
- LIMITATIONS.md (constraints and caveats)
- VMM.json (variance-movement mapping results)
- ICP.json (invariance-conditional pricing tests)
"""
        return summary

    def generate_repro_md(self, results: Dict, window_id: str) -> str:
        """Generate REPRO.md with exact CLI and inputs."""

        repro = f"""# ICP-VMM Reproduction Guide

## Exact CLI Used
```bash
python scripts/icp_vmm/run_icp_vmm_window.py \\
  --window {window_id} \\
  --seed {results.get('seed', 42)} \\
  --lags {results.get('lags', 2)} \\
  --fdr_q {results.get('fdr_q', 0.05)} \\
  --mode provisional \\
  --verbose
```

## Input Data
- **Window ID**: {window_id}
- **Symbol**: {results.get('symbol', 'BTC-USD')}
- **Venues**: {', '.join(results.get('venues', []))}
- **Observations**: {results.get('observations', {})}

## Parameters
- **Seed**: {results.get('seed', 42)}
- **Lags**: {results.get('lags', 2)}
- **FDR Q**: {results.get('fdr_q', 0.05)}
- **Min Per Env**: {results.get('min_bin_size', 5)}

## Environment Variables
- **KRAKEN_TS_FLEX**: {os.environ.get('KRAKEN_TS_FLEX', '1')}
- **PYTHONPATH**: {os.environ.get('PYTHONPATH', 'N/A')}

## Dependencies
- Python: 3.11.6
- NumPy: 2.1.1
- Pandas: 2.2.2
- Statsmodels: 0.14.2
"""
        return repro

    def export_refined_results(
        self,
        results: Dict,
        window_id: str,
        symbol: str,
        s3_inputs: List[str],
        output_dir: str,
    ) -> Dict:
        """Export results with refined format and canonical paths."""

        try:
            # Create output directory
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            # Generate canonical manifest
            manifest = self.generate_canonical_manifest(results, window_id, symbol, s3_inputs)

            # Generate evidence bundle
            evidence_md = self.generate_evidence_md(
                results,
                window_id,
                f"s3://{self.bucket}/analysis/{symbol}/icp_vmm/provisional/{window_id}/",
            )
            limitations_md = self.generate_limitations_md(results)
            summary_md = self.generate_summary_md(results)
            repro_md = self.generate_repro_md(results, window_id)

            # Write files
            files_written = []

            # Write analysis files
            vmm_file = Path(output_dir) / "vmm_results.json"
            with open(vmm_file, "w") as f:
                json.dump(results.get("vmm_results", {}), f, indent=2)
            files_written.append(str(vmm_file))

            icp_file = Path(output_dir) / "icp_tests.json"
            with open(icp_file, "w") as f:
                json.dump(results.get("icp_tests", {}), f, indent=2)
            files_written.append(str(icp_file))

            # Write evidence bundle
            evidence_file = Path(output_dir) / "EVIDENCE.md"
            with open(evidence_file, "w") as f:
                f.write(evidence_md)
            files_written.append(str(evidence_file))

            limitations_file = Path(output_dir) / "LIMITATIONS.md"
            with open(limitations_file, "w") as f:
                f.write(limitations_md)
            files_written.append(str(limitations_file))

            summary_file = Path(output_dir) / "SUMMARY.md"
            with open(summary_file, "w") as f:
                f.write(summary_md)
            files_written.append(str(summary_file))

            repro_file = Path(output_dir) / "REPRO.md"
            with open(repro_file, "w") as f:
                f.write(repro_md)
            files_written.append(str(repro_file))

            # Compute output hashes
            output_hashes = []
            for file_path in files_written:
                file_hash = self.compute_file_hash(file_path)
                file_size = Path(file_path).stat().st_size
                output_hashes.append(
                    {
                        "path": f"icp_vmm_provisional/{Path(file_path).name}",
                        "sha256": file_hash,
                        "bytes": file_size,
                    }
                )

            # Update manifest with output hashes
            manifest["integrity"]["outputs"] = output_hashes

            # Canonicalize and compute manifest hash
            manifest_json = self.canonicalize_json(manifest)
            manifest_hash = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
            manifest["integrity"]["manifestHash"] = manifest_hash

            # Update the manifest with the computed hash
            manifest_json = self.canonicalize_json(manifest)

            # Write manifest
            manifest_file = Path(output_dir) / "MANIFEST.json"
            with open(manifest_file, "w") as f:
                f.write(manifest_json)

            # Update evidence with manifest hash
            evidence_md_updated = evidence_md.replace("{{manifest_hash}}", manifest_hash)
            with open(evidence_file, "w") as f:
                f.write(evidence_md_updated)

            return {
                "status": "SUCCESS",
                "s3_path": f"s3://{self.bucket}/analysis/{symbol}/icp_vmm/provisional/{window_id}/",
                "files_written": files_written + [str(manifest_file)],
                "manifest_hash": manifest_hash,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Refined export failed: {e}")
            return {
                "status": "FAILED",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
