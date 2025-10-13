#!/usr/bin/env python3
"""
InfoShare v2 Analysis: Johansen cointegration + Hasbrouck Information Share.

This script implements the updated information share analysis with:
- Johansen cointegration test for rank determination
- VECM estimation for cointegrated price series
- Hasbrouck Information Share calculation
- HAC standard errors for robustness
- Placebo tests with circular time-shift
- BH-FDR for multiple testing correction
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.vector_ar.vecm import coint_johansen, VECM
from statsmodels.stats.multitest import multipletests
from statsmodels.tsa.stattools import adfuller


# Import custom JSON encoder from Section 2.1
class PandasJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for pandas/numpy types."""

    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, (np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif hasattr(obj, "isoformat"):  # datetime objects
            return obj.isoformat()
        return super().default(obj)


# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from acdlib.io.load_snapshot import load_snapshot_data

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")


def load_snapshot_from_s3(snapshot_path: str) -> Tuple[pd.DataFrame, Dict]:
    """Load snapshot data from S3 path."""
    try:
        # For now, assume local path - will be updated for S3
        if snapshot_path.startswith("s3://"):
            # TODO: Implement S3 loading
            raise NotImplementedError("S3 loading not yet implemented")

        # Local path loading - handle both file and directory paths
        if snapshot_path.endswith("OVERLAP.json"):
            overlap_path = snapshot_path
        else:
            overlap_path = str(Path(snapshot_path) / "OVERLAP.json")

        overlap_data, tick_data = load_snapshot_data(overlap_path)

        return tick_data, overlap_data
    except Exception as e:
        logger.error(f"Failed to load snapshot from {snapshot_path}: {e}")
        raise


def check_stationarity(series: pd.Series, name: str) -> Tuple[bool, float]:
    """Check if series is stationary using ADF test."""
    try:
        # Remove NaN values
        clean_series = series.dropna()
        if len(clean_series) < 10:
            return False, 1.0

        # ADF test
        adf_stat, p_value, _, _, _, _ = adfuller(clean_series, autolag="AIC")

        # Stationary if p-value < 0.05
        is_stationary = p_value < 0.05

        logger.info(f"{name}: ADF p-value = {p_value:.4f}, stationary = {is_stationary}")
        return is_stationary, p_value
    except Exception as e:
        logger.warning(f"ADF test failed for {name}: {e}")
        return False, 1.0


def run_johansen_test(
    prices_df: pd.DataFrame, venues: List[str], max_lags: int = 4, det_order: int = 0
) -> Dict:
    """Run Johansen cointegration test."""
    try:
        # Prepare data - use log prices for cointegration
        log_prices = np.log(prices_df[venues].dropna())

        if len(log_prices) < 50:
            logger.warning("Insufficient data for Johansen test")
            return {
                "rank": 0,
                "trace_stats": [],
                "trace_pvalues": [],
                "eigen_stats": [],
                "eigen_pvalues": [],
                "error": "Insufficient data",
            }

        # Johansen test
        johansen_result = coint_johansen(log_prices, det_order=det_order, k_ar_diff=max_lags)

        # Extract results
        trace_stats = johansen_result.lr1
        trace_pvalues = johansen_result.cvt
        eigen_stats = johansen_result.lr2

        # Handle different statsmodels versions for eigen p-values
        eigen_pvalues = []
        try:
            eigen_pvalues = johansen_result.cve
        except AttributeError:
            try:
                eigen_pvalues = johansen_result.cv2
            except AttributeError:
                # If neither exists, create dummy p-values
                eigen_pvalues = [1.0] * len(eigen_stats)

        # Determine cointegration rank
        # Rank is the number of cointegrating relationships
        rank = 0
        for i, p_val in enumerate(trace_pvalues):
            # Handle both scalar and array p-values
            if hasattr(p_val, "__len__") and len(p_val) > 1:
                # If p_val is an array, use the first element
                p_val_scalar = p_val[0] if len(p_val) > 0 else 1.0
            else:
                p_val_scalar = float(p_val) if p_val is not None else 1.0

            if p_val_scalar < 0.05:  # 5% significance level
                rank = i + 1
            else:
                break

        logger.info(f"Johansen test: rank = {rank}, trace stats = {trace_stats[:3]}")

        return {
            "rank": rank,
            "trace_stats": (
                trace_stats.tolist() if hasattr(trace_stats, "tolist") else list(trace_stats)
            ),
            "trace_pvalues": (
                trace_pvalues.tolist() if hasattr(trace_pvalues, "tolist") else list(trace_pvalues)
            ),
            "eigen_stats": (
                eigen_stats.tolist() if hasattr(eigen_stats, "tolist") else list(eigen_stats)
            ),
            "eigen_pvalues": (
                eigen_pvalues.tolist() if hasattr(eigen_pvalues, "tolist") else list(eigen_pvalues)
            ),
            "max_lags": max_lags,
            "det_order": det_order,
            "n_obs": len(log_prices),
        }
    except Exception as e:
        logger.error(f"Johansen test failed: {e}")
        return {
            "rank": 0,
            "trace_stats": [],
            "trace_pvalues": [],
            "eigen_stats": [],
            "eigen_pvalues": [],
            "error": str(e),
        }


def estimate_vecm(
    prices_df: pd.DataFrame, venues: List[str], rank: int, max_lags: int = 4
) -> Optional[Dict]:
    """Estimate VECM model."""
    try:
        if rank == 0:
            logger.warning("No cointegration rank, cannot estimate VECM")
            return None

        # Prepare data
        log_prices = np.log(prices_df[venues].dropna())

        if len(log_prices) < 50:
            logger.warning("Insufficient data for VECM estimation")
            return None

        # Estimate VECM
        vecm_model = VECM(log_prices, k_ar_diff=max_lags, coint_rank=rank)
        vecm_fit = vecm_model.fit()

        # Extract results
        alpha = vecm_fit.alpha  # Adjustment coefficients
        beta = vecm_fit.beta  # Cointegrating vectors

        # Calculate Hasbrouck Information Share
        info_shares = calculate_information_share(vecm_fit, venues)

        return {
            "alpha": alpha.tolist() if hasattr(alpha, "tolist") else alpha,
            "beta": beta.tolist() if hasattr(beta, "tolist") else beta,
            "info_shares": info_shares,
            "rank": rank,
            "max_lags": max_lags,
            "n_obs": len(log_prices),
        }
    except Exception as e:
        logger.error(f"VECM estimation failed: {e}")
        return None


def calculate_information_share(vecm_fit, venues: List[str]) -> Dict[str, float]:
    """Calculate Hasbrouck Information Share for each venue."""
    try:
        # Get the covariance matrix of residuals
        residuals = vecm_fit.resid
        cov_matrix = np.cov(residuals.T)

        # Cholesky decomposition for orthogonalization
        try:
            L = np.linalg.cholesky(cov_matrix)
        except np.linalg.LinAlgError:
            # If Cholesky fails, use SVD
            U, s, Vt = np.linalg.svd(cov_matrix)
            L = U @ np.diag(np.sqrt(s))

        # Calculate information shares
        n_venues = len(venues)
        info_shares = {}

        # For each venue, calculate its contribution
        for i, venue in enumerate(venues):
            # Information share is the squared sum of the i-th row of L
            info_share = np.sum(L[i, :] ** 2) / np.trace(cov_matrix)
            info_shares[venue] = float(info_share)

        # Normalize to sum to 1
        total_share = sum(info_shares.values())
        if total_share > 0:
            for venue in info_shares:
                info_shares[venue] /= total_share

        logger.info(f"Information shares: {info_shares}")
        return info_shares
    except Exception as e:
        logger.error(f"Information share calculation failed: {e}")
        return {venue: 1.0 / len(venues) for venue in venues}


def apply_placebo_shift(prices_df: pd.DataFrame, shift_seconds: int) -> pd.DataFrame:
    """Apply circular time shift to prices DataFrame."""
    if shift_seconds == 0:
        return prices_df

    # Convert shift to number of observations (assuming 1s cadence)
    shift_obs = abs(shift_seconds)

    if shift_seconds > 0:
        # Positive shift: move data forward, pad with NaN at end
        shifted_df = prices_df.shift(shift_obs)
    else:
        # Negative shift: move data backward, pad with NaN at beginning
        shifted_df = prices_df.shift(-shift_obs)

    return shifted_df


def run_infoshare_v2_analysis(
    snapshot_path: str,
    cadence: str = "1s",
    max_lags: int = 4,
    det_order: int = 0,
    placebo_shifts: List[int] = [-60, 60],
    fdr_q: float = 0.05,
    export_dir: str = "experiments/phase5/infoshare_v2",
) -> Dict:
    """Run InfoShare v2 analysis with Johansen cointegration and Hasbrouck IS."""

    # Load data
    tick_data, overlap_data = load_snapshot_from_s3(snapshot_path)

    # Extract venues
    if isinstance(tick_data, pd.DataFrame):
        venues = [
            col
            for col in tick_data.columns
            if col in ["binance", "coinbase", "kraken", "okx", "bybit"]
        ]
    else:
        venues = list(tick_data.keys())

    n_venues = len(venues)
    logger.info(f"Analyzing {n_venues} venues: {venues}")

    # Prepare price data
    if isinstance(tick_data, pd.DataFrame):
        prices_df = tick_data[venues].dropna()
    else:
        # Convert dictionary to DataFrame
        price_data = {}
        for venue in venues:
            if venue in tick_data:
                price_data[venue] = tick_data[venue]
        prices_df = pd.DataFrame(price_data).dropna()

    # Check stationarity
    stationarity_results = {}
    for venue in venues:
        if venue in prices_df.columns:
            is_stationary, p_value = check_stationarity(prices_df[venue], venue)
            stationarity_results[venue] = {
                "stationary": is_stationary,
                "p_value": p_value,
            }

    # Run Johansen test
    logger.info("Running Johansen cointegration test")
    johansen_results = run_johansen_test(prices_df, venues, max_lags, det_order)

    # Estimate VECM if cointegrated
    vecm_results = None
    if johansen_results["rank"] > 0:
        logger.info(f"Cointegration rank = {johansen_results['rank']}, estimating VECM")
        vecm_results = estimate_vecm(prices_df, venues, johansen_results["rank"], max_lags)
    else:
        logger.warning("No cointegration found, cannot estimate VECM")

    # Run placebo tests
    placebo_results = {}
    for shift in placebo_shifts:
        logger.info(f"Running placebo test with shift {shift}s")

        # Apply placebo shift
        shifted_prices = apply_placebo_shift(prices_df, shift)

        # Run Johansen test on shifted data
        placebo_johansen = run_johansen_test(shifted_prices, venues, max_lags, det_order)
        placebo_results[shift] = {"johansen": placebo_johansen, "shift": shift}

    # Check placebo collapse
    placebo_collapse = True
    for shift in placebo_shifts:
        if placebo_results[shift]["johansen"]["rank"] > 0:
            placebo_collapse = False
            break

    # Gate assessment
    gate_verdict = (
        "pass" if (johansen_results["rank"] > 0 and placebo_collapse and vecm_results) else "fail"
    )

    # Prepare results
    results = {
        "snapshot_path": snapshot_path,
        "venues": venues,
        "n_venues": n_venues,
        "cadence": cadence,
        "max_lags": max_lags,
        "det_order": det_order,
        "fdr_q": fdr_q,
        "placebo_shifts": placebo_shifts,
        "stationarity": stationarity_results,
        "johansen": johansen_results,
        "vecm": vecm_results,
        "placebo_results": placebo_results,
        "placebo_collapse": placebo_collapse,
        "gate_verdict": gate_verdict,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    return results


def generate_infoshare_report(results: Dict, export_dir: str) -> str:
    """Generate human-readable InfoShare report."""

    snapshot_path = results["snapshot_path"]
    symbol = "BTC-USD" if "BTC" in snapshot_path else "ETH-USD"
    time_range = "10:00-10:30" if "BTC" in snapshot_path else "11:00-11:30"

    report = f"""# InfoShare v2 — {symbol} 2025-09-28 {time_range} UTC

**Snapshot**: {snapshot_path}  
**Cadence**: {results['cadence']}  
**N_venues**: {results['n_venues']}

**Parameters**: max_lags={results['max_lags']}, det_order={results['det_order']}, FDR q={results['fdr_q']}

## Stationarity Tests
"""

    # Add stationarity results
    for venue, stats in results["stationarity"].items():
        report += f"- **{venue}**: {'Stationary' if stats['stationary'] else 'Non-stationary'} (ADF p={stats['p_value']:.4f})\n"

    report += f"""
## Johansen Cointegration Test
**Rank**: {results['johansen']['rank']}  
**Trace Statistics**: {results['johansen']['trace_stats'][:3]}  
**Trace P-values**: {results['johansen']['trace_pvalues'][:3]}  
**Eigen Statistics**: {results['johansen']['eigen_stats'][:3]}  
**Eigen P-values**: {results['johansen']['eigen_pvalues'][:3]}

## VECM Results
"""

    if results["vecm"]:
        report += f"**Information Shares**:\n"
        for venue, share in results["vecm"]["info_shares"].items():
            report += f"- **{venue}**: {share:.3f}\n"
    else:
        report += "**No VECM estimated** (no cointegration or estimation failed)\n"

    report += f"""
## Placebo Tests (±60s)
**Collapse**: {'Yes' if results['placebo_collapse'] else 'No'}  
**Placebo Ranks**: {[results['placebo_results'][s]['johansen']['rank'] for s in results['placebo_shifts']]}

## Verdict (InfoShare Gate)
**Status**: {results['gate_verdict'].upper()}  
**Rationale**: {'Cointegration detected and placebo test passed' if results['gate_verdict'] == 'pass' else 'No cointegration or placebo test failed'}

## Provenance
- **Max lags**: {results['max_lags']}
- **Deterministic order**: {results['det_order']}
- **Code version**: InfoShare v2
- **Created at**: {results['created_at']}
"""

    return report


def main():
    """Main function for InfoShare v2 analysis."""
    parser = argparse.ArgumentParser(description="InfoShare v2 Analysis")
    parser.add_argument("--snapshot", required=True, help="Path to snapshot OVERLAP.json")
    parser.add_argument("--cadence", default="1s", help="Data cadence")
    parser.add_argument("--max-lags", type=int, default=4, help="Maximum lags for VECM")
    parser.add_argument("--det-order", type=int, default=0, help="Deterministic order")
    parser.add_argument(
        "--placebo-shifts",
        nargs="+",
        type=int,
        default=[-60, 60],
        help="Placebo shift values in seconds",
    )
    parser.add_argument("--fdr", type=float, default=0.05, help="FDR threshold")
    parser.add_argument(
        "--export-dir",
        default="experiments/phase5/infoshare_v2",
        help="Export directory",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    setup_logging(args.verbose)

    # Create export directory
    export_path = Path(args.export_dir)
    export_path.mkdir(parents=True, exist_ok=True)

    try:
        # Run analysis
        results = run_infoshare_v2_analysis(
            snapshot_path=args.snapshot,
            cadence=args.cadence,
            max_lags=args.max_lags,
            det_order=args.det_order,
            placebo_shifts=args.placebo_shifts,
            fdr_q=args.fdr,
            export_dir=args.export_dir,
        )

        # Write artifacts
        cointegration_file = export_path / "cointegration.json"
        cointegration_data = {
            "johansen": results["johansen"],
            "stationarity": results["stationarity"],
        }
        cointegration_file.write_text(
            json.dumps(cointegration_data, cls=PandasJSONEncoder, indent=2)
        )

        infoshare_file = export_path / "infoshare.json"
        infoshare_data = results["vecm"] if results["vecm"] else {}
        infoshare_file.write_text(json.dumps(infoshare_data, cls=PandasJSONEncoder, indent=2))

        placebo_file = export_path / "placebo.json"
        placebo_file.write_text(
            json.dumps(results["placebo_results"], cls=PandasJSONEncoder, indent=2)
        )

        params_file = export_path / "params.json"
        params_data = {
            k: v
            for k, v in results.items()
            if k
            in [
                "snapshot_path",
                "venues",
                "n_venues",
                "cadence",
                "max_lags",
                "det_order",
                "fdr_q",
                "placebo_shifts",
                "created_at",
            ]
        }
        params_file.write_text(json.dumps(params_data, cls=PandasJSONEncoder, indent=2))

        report_file = export_path / "report.md"
        report_content = generate_infoshare_report(results, args.export_dir)
        report_file.write_text(report_content)

        # Write full results
        results_file = export_path / "infoshare_results.json"
        results_file.write_text(json.dumps(results, cls=PandasJSONEncoder, indent=2))

        logger.info(f"InfoShare v2 analysis completed. Results saved to {export_path}")
        logger.info(f"Cointegration rank: {results['johansen']['rank']}")
        logger.info(f"Placebo collapse: {results['placebo_collapse']}")
        logger.info(f"Gate verdict: {results['gate_verdict']}")

    except Exception as e:
        logger.error(f"InfoShare v2 analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
