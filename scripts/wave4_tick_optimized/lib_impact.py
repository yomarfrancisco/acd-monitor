"""
Price Impact Spillovers Analysis (Vectorized).
Implements H3: Large trades on venue A cause short-horizon returns on venue B.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


def identify_large_trade_events(df: pd.DataFrame, percentile: float = 95.0) -> pd.DataFrame:
    """Identify large trade events for impact analysis."""
    if df.empty:
        return df

    threshold = df["base_amount"].quantile(percentile / 100)
    large_events = df[df["base_amount"] >= threshold].copy()

    logger.info(f"Identified {len(large_events):,} large trade events (≥{threshold:.4f})")
    return large_events


def calculate_cumulative_returns(
    df: pd.DataFrame, event_times: pd.Series, pre_window: int = 10, post_window: int = 20
) -> Dict:
    """Calculate cumulative returns around large trade events."""
    if df.empty or event_times.empty:
        return {"events": 0, "avg_cumulative_return": 0.0, "max_impact": 0.0, "time_to_peak": 0}

    # Calculate returns
    df["returns"] = df["price"].pct_change()

    cumulative_returns = []
    max_impacts = []
    time_to_peaks = []

    for event_time in event_times:
        # Find event bin
        event_bin = (
            df[df["time_exchange"] <= event_time]["bin50"].iloc[-1]
            if len(df[df["time_exchange"] <= event_time]) > 0
            else None
        )

        if event_bin is not None:
            # Get window around event
            start_bin = event_bin - pre_window
            end_bin = event_bin + post_window

            window_data = df[(df["bin50"] >= start_bin) & (df["bin50"] <= end_bin)]

            if len(window_data) > 1:
                # Calculate cumulative returns
                cum_returns = window_data["returns"].cumsum()

                # Find peak impact
                max_impact = cum_returns.max()
                time_to_peak = (
                    cum_returns.idxmax() - cum_returns.idxmin()
                    if cum_returns.idxmax() != cum_returns.idxmin()
                    else 0
                )

                cumulative_returns.append(cum_returns.iloc[-1])  # Final cumulative return
                max_impacts.append(max_impact)
                time_to_peaks.append(time_to_peak)

    if not cumulative_returns:
        return {"events": 0, "avg_cumulative_return": 0.0, "max_impact": 0.0, "time_to_peak": 0}

    return {
        "events": len(cumulative_returns),
        "avg_cumulative_return": float(np.mean(cumulative_returns)),
        "max_impact": float(np.mean(max_impacts)),
        "time_to_peak": float(np.mean(time_to_peaks)),
        "cumulative_returns": cumulative_returns,
        "max_impacts": max_impacts,
        "time_to_peaks": time_to_peaks,
    }


def bootstrap_impact_baseline(df: pd.DataFrame, n_bootstrap: int = 200) -> Dict:
    """Bootstrap baseline for impact analysis."""
    if df.empty:
        return {"mean_impact": 0.0, "std_impact": 0.0, "p_value": 1.0}

    # Sample random events
    n_events = min(100, len(df) // 10)  # Limit to 100 events
    impacts = []

    for _ in range(n_bootstrap):
        # Randomly sample events
        random_events = df.sample(n=min(n_events, len(df)))

        if len(random_events) > 0:
            # Calculate returns for random events
            random_returns = random_events["price"].pct_change().dropna()

            if len(random_returns) > 0:
                avg_impact = random_returns.abs().mean()
                impacts.append(avg_impact)

    if not impacts:
        return {"mean_impact": 0.0, "std_impact": 0.0, "p_value": 1.0}

    mean_impact = np.mean(impacts)
    std_impact = np.std(impacts)

    return {"mean_impact": float(mean_impact), "std_impact": float(std_impact), "impacts": impacts}


def analyze_impact_spillovers(
    venue1_data: pd.DataFrame, venue2_data: pd.DataFrame, venue1_name: str, venue2_name: str
) -> Dict:
    """Analyze price impact spillovers from venue1 to venue2."""
    logger.info(f"Analyzing impact spillovers from {venue1_name} to {venue2_name}")

    # Identify large trade events on venue1
    large_events1 = identify_large_trade_events(venue1_data)

    if large_events1.empty or venue2_data.empty:
        return {
            "venue1": venue1_name,
            "venue2": venue2_name,
            "status": "NO DATA FOUND",
            "events1": 0,
            "bins2": 0,
        }

    # Calculate impact on venue2
    impact_results = calculate_cumulative_returns(venue2_data, large_events1["time_exchange"])

    if impact_results["events"] == 0:
        return {
            "venue1": venue1_name,
            "venue2": venue2_name,
            "status": "NO IMPACT EVENTS",
            "events1": len(large_events1),
            "bins2": len(venue2_data),
        }

    # Bootstrap baseline
    bootstrap_results = bootstrap_impact_baseline(venue2_data)

    # Calculate p-value
    observed_impact = impact_results["max_impact"]
    bootstrap_impacts = bootstrap_results["impacts"]
    p_value = np.mean([impact >= observed_impact for impact in bootstrap_impacts])

    return {
        "venue1": venue1_name,
        "venue2": venue2_name,
        "status": "SUCCESS",
        "events1": len(large_events1),
        "bins2": len(venue2_data),
        "impact_events": impact_results["events"],
        "avg_cumulative_return": impact_results["avg_cumulative_return"],
        "max_impact": impact_results["max_impact"],
        "time_to_peak": impact_results["time_to_peak"],
        "bootstrap_mean": bootstrap_results["mean_impact"],
        "bootstrap_std": bootstrap_results["std_impact"],
        "impact_ratio": (
            observed_impact / bootstrap_results["mean_impact"]
            if bootstrap_results["mean_impact"] != 0
            else 0
        ),
        "p_value": p_value,
        "significant": p_value < 0.05,
    }
