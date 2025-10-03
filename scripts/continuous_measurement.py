#!/usr/bin/env python3
"""
Continuous Variable Measurement System
Captures all fully measurable variables from S3 tick data and stores to S3
"""

import json
import boto3
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
import argparse
import sys
from typing import Dict, List, Any
import logging
from schema_validator import SchemaValidator

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ContinuousMeasurement:
    def __init__(self, bucket: str = "acd-monitor-snapshots", prefix: str = "snapshots"):
        self.s3 = boto3.client("s3")
        self.bucket = bucket
        self.prefix = prefix
        self.schema_validator = SchemaValidator()

    def load_tick_data(self, symbol: str, date: str, time_range: str) -> Dict[str, pd.DataFrame]:
        """Load tick data for all venues from S3"""
        venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        data = {}

        for venue in venues:
            try:
                key = f"{self.prefix}/{symbol}/{date}/{time_range}/ticks/{venue}/part-0000.parquet"

                # Download to local temp file first
                import tempfile

                with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
                    self.s3.download_file(self.bucket, key, tmp_file.name)
                    df = pd.read_parquet(tmp_file.name)
                    df["ts_exchange"] = pd.to_datetime(df["ts_exchange"])
                    data[venue] = df
                    logger.info(f"Loaded {len(df)} ticks for {venue}")

                    # Clean up temp file
                    import os

                    os.unlink(tmp_file.name)

            except Exception as e:
                logger.warning(f"Failed to load data for {venue}: {e}")
                continue

        return data

    def calculate_vwap(self, df: pd.DataFrame) -> float:
        """Calculate VWAP from tick data"""
        if len(df) == 0:
            return np.nan

        # Check if required columns exist
        if "last_px" not in df.columns or "last_sz" not in df.columns:
            # Fallback to simple average price if volume data missing
            return df["last_px"].mean() if "last_px" in df.columns else np.nan

        # VWAP = sum(price * volume) / sum(volume)
        return (df["last_px"] * df["last_sz"]).sum() / df["last_sz"].sum()

    def calculate_highs_lows(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate daily/weekly/monthly highs and lows"""
        if len(df) == 0:
            return {
                "high_24h": np.nan,
                "low_24h": np.nan,
                "high_7d": np.nan,
                "low_7d": np.nan,
            }

        # For this implementation, we'll use the window data
        # In production, this would aggregate across longer timeframes
        return {
            "high_24h": df["last_px"].max(),
            "low_24h": df["last_px"].min(),
            "high_7d": df["last_px"].max(),  # Placeholder - would need historical data
            "low_7d": df["last_px"].min(),  # Placeholder - would need historical data
        }

    def classify_trading_session(self, timestamp: datetime) -> str:
        """Classify trading session based on UTC timestamp"""
        hour = timestamp.hour

        if 0 <= hour < 8:
            return "Asia"
        elif 8 <= hour < 16:
            return "Europe"
        elif 16 <= hour < 24:
            return "US"
        else:
            return "Overlap"

    def calculate_volatility(self, df: pd.DataFrame, window: str = "1m") -> float:
        """Calculate realized volatility"""
        if len(df) < 2:
            return np.nan

        # Calculate returns
        returns = df["last_px"].pct_change().dropna()
        if len(returns) == 0:
            return np.nan

        # Annualized volatility
        return returns.std() * np.sqrt(365 * 24 * 60)  # Assuming minute data

    def calculate_spread_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate spread metrics"""
        if len(df) == 0:
            return {"spread_bps_mean": np.nan, "spread_bps_std": np.nan}

        # Check if spread_bps column exists
        if "spread_bps" in df.columns:
            return {
                "spread_bps_mean": df["spread_bps"].mean(),
                "spread_bps_std": df["spread_bps"].std(),
            }
        elif "best_bid" in df.columns and "best_ask" in df.columns:
            # Calculate spread from bid/ask if spread_bps missing
            spread = ((df["best_ask"] - df["best_bid"]) / df["best_bid"] * 10000).mean()
            return {
                "spread_bps_mean": spread,
                "spread_bps_std": (
                    (df["best_ask"] - df["best_bid"]) / df["best_bid"] * 10000
                ).std(),
            }
        else:
            return {"spread_bps_mean": np.nan, "spread_bps_std": np.nan}

    def calculate_lead_lag(self, data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Calculate lead-lag relationships between venues"""
        if len(data) < 2:
            return {}

        lead_lag = {}
        venues = list(data.keys())

        for i, venue1 in enumerate(venues):
            for venue2 in venues[i + 1 :]:
                try:
                    df1 = data[venue1].set_index("ts_exchange")["last_px"]
                    df2 = data[venue2].set_index("ts_exchange")["last_px"]

                    # Align timestamps and calculate correlation
                    aligned = pd.concat([df1, df2], axis=1, join="inner")
                    if len(aligned) > 10:  # Minimum data requirement
                        corr = aligned.corr().iloc[0, 1]
                        lead_lag[f"{venue1}_vs_{venue2}"] = corr
                except Exception as e:
                    logger.warning(f"Failed to calculate lead-lag for {venue1} vs {venue2}: {e}")
                    continue

        return lead_lag

    def calculate_infoshare(self, data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Calculate information share for each venue"""
        if len(data) < 2:
            return {}

        infoshare = {}
        venues = list(data.keys())

        try:
            # Create price matrix
            price_data = {}
            for venue in venues:
                df = data[venue].set_index("ts_exchange")["last_px"]
                price_data[venue] = df

            # Align all data
            aligned = pd.concat(price_data.values(), axis=1, keys=price_data.keys(), join="inner")

            if len(aligned) > 50:  # Minimum data requirement
                # Calculate information share (simplified version)
                for venue in venues:
                    # Information share as proportion of price variance explained
                    venue_returns = aligned[venue].pct_change().dropna()
                    total_variance = aligned.pct_change().var().sum()
                    venue_variance = venue_returns.var()
                    infoshare[venue] = venue_variance / total_variance if total_variance > 0 else 0

        except Exception as e:
            logger.warning(f"Failed to calculate information share: {e}")

        return infoshare

    def calculate_liquidity_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate advanced liquidity metrics from bid/ask size data"""
        if len(df) == 0:
            return {
                "liquidity_score": np.nan,
                "depth_imbalance": np.nan,
                "liquidity_volatility": np.nan,
                "market_impact": np.nan,
                "liquidity_ratio": np.nan,
            }

        # Basic liquidity metrics
        avg_bid_size = df["bid_sz"].mean()
        avg_ask_size = df["ask_sz"].mean()
        liquidity_score = (avg_bid_size + avg_ask_size) / 2
        depth_imbalance = (
            (avg_bid_size - avg_ask_size) / (avg_bid_size + avg_ask_size)
            if (avg_bid_size + avg_ask_size) > 0
            else 0
        )

        # Advanced liquidity metrics
        # 1. Liquidity Volatility - variance of available depth over time
        total_depth = df["bid_sz"] + df["ask_sz"]
        liquidity_volatility = total_depth.std() if len(total_depth) > 1 else 0

        # 2. Market Impact - spread sensitivity to order size
        if len(df) > 1:
            size_changes = df["last_sz"].diff().abs()
            spread_changes = df["spread_bps"].diff().abs()
            if size_changes.sum() > 0:
                market_impact = (size_changes * spread_changes).sum() / size_changes.sum()
            else:
                market_impact = 0
        else:
            market_impact = 0

        # 3. Liquidity Ratio - ratio of available depth to realized volume
        total_volume = df["last_sz"].sum()
        total_depth_sum = total_depth.sum()
        liquidity_ratio = total_depth_sum / total_volume if total_volume > 0 else 0

        return {
            "liquidity_score": liquidity_score,
            "depth_imbalance": depth_imbalance,
            "liquidity_volatility": liquidity_volatility,
            "market_impact": market_impact,
            "liquidity_ratio": liquidity_ratio,
        }

    def calculate_leadership_shares(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Calculate advanced leadership shares with multiple weighting schemes"""
        if len(data) == 0:
            return {}

        venues = list(data.keys())
        results = {}

        # 1. Volume-Weighted Leadership
        venue_volumes = {}
        for venue, df in data.items():
            if len(df) > 0:
                venue_volumes[venue] = df["last_sz"].sum()
            else:
                venue_volumes[venue] = 0

        total_volume = sum(venue_volumes.values())
        volume_weighted = {
            venue: vol / total_volume if total_volume > 0 else 0
            for venue, vol in venue_volumes.items()
        }

        # 2. Price Impact Leadership
        price_impact = {}
        for venue in venues:
            if venue in data and len(data[venue]) > 0:
                df = data[venue]
                if len(df) > 1:
                    volume_changes = df["last_sz"].diff().abs()
                    price_changes = df["last_px"].pct_change().abs()
                    if volume_changes.sum() > 0 and price_changes.sum() > 0:
                        price_impact[venue] = (
                            volume_changes * price_changes
                        ).sum() / volume_changes.sum()
                    else:
                        price_impact[venue] = 0
                else:
                    price_impact[venue] = 0
            else:
                price_impact[venue] = 0

        # Normalize price impact
        total_impact = sum(price_impact.values())
        price_impact_normalized = {
            venue: impact / total_impact if total_impact > 0 else 0
            for venue, impact in price_impact.items()
        }

        # 3. Information Leadership (variance contribution)
        info_leadership = {}
        for venue in venues:
            if venue in data and len(data[venue]) > 0:
                df = data[venue]
                if len(df) > 1:
                    price_returns = df["last_px"].pct_change().dropna()
                    info_leadership[venue] = price_returns.var() if len(price_returns) > 0 else 0
                else:
                    info_leadership[venue] = 0
            else:
                info_leadership[venue] = 0

        # Normalize information leadership
        total_info = sum(info_leadership.values())
        info_leadership_normalized = {
            venue: info / total_info if total_info > 0 else 0
            for venue, info in info_leadership.items()
        }

        # 4. Venue Specialization
        venue_specialization = {}
        for venue in venues:
            if venue in data and len(data[venue]) > 0:
                df = data[venue]
                # Spread specialist (inverse spread)
                avg_spread = df["spread_bps"].mean()
                spread_specialist = 1 / (1 + avg_spread) if avg_spread > 0 else 0

                # Volume specialist
                total_volume = df["last_sz"].sum()

                # Volatility specialist
                if len(df) > 1:
                    price_volatility = df["last_px"].pct_change().std()
                else:
                    price_volatility = 0

                # Liquidity specialist
                avg_depth = (df["bid_sz"] + df["ask_sz"]).mean()

                venue_specialization[venue] = {
                    "spread_specialist": spread_specialist,
                    "volume_specialist": total_volume,
                    "volatility_specialist": price_volatility,
                    "liquidity_specialist": avg_depth,
                }
            else:
                venue_specialization[venue] = {
                    "spread_specialist": 0,
                    "volume_specialist": 0,
                    "volatility_specialist": 0,
                    "liquidity_specialist": 0,
                }

        # Normalize specialization scores
        for metric in [
            "spread_specialist",
            "volume_specialist",
            "volatility_specialist",
            "liquidity_specialist",
        ]:
            values = [venue_specialization[venue][metric] for venue in venues]
            total = sum(values)
            if total > 0:
                for venue in venues:
                    venue_specialization[venue][metric] = (
                        venue_specialization[venue][metric] / total
                    )

        results = {
            "volume_weighted": volume_weighted,
            "price_impact": price_impact_normalized,
            "information_leadership": info_leadership_normalized,
            "venue_specialization": venue_specialization,
        }

        return results

    def process_window(self, symbol: str, date: str, time_range: str) -> Dict[str, Any]:
        """Process a single window and calculate all metrics"""
        logger.info(f"Processing {symbol} {date} {time_range}")

        # Load tick data
        data = self.load_tick_data(symbol, date, time_range)
        if not data:
            logger.error(f"No data found for {symbol} {date} {time_range}")
            return {}

        # Validate schema for enhanced metrics
        enhanced_metrics_available, schema_result = self.schema_validator.validate_schema(data)

        # Initialize results
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "date": date,
            "time_range": time_range,
            "provenance": "REAL",
            "regulatory_grade": True,
            "schema_status": schema_result["schema_status"],
            "enhanced_metrics": enhanced_metrics_available,
            "metrics": {},
        }

        # Calculate metrics for each venue
        for venue, df in data.items():
            if len(df) == 0:
                continue

            # Basic metrics (always available)
            venue_metrics = {
                "vwap": self.calculate_vwap(df),
                "highs_lows": self.calculate_highs_lows(df),
                "session": self.classify_trading_session(df["ts_exchange"].iloc[0]),
                "volatility_1m": self.calculate_volatility(df),
                "spread_metrics": self.calculate_spread_metrics(df),
            }

            # Enhanced metrics (only if schema is complete)
            if enhanced_metrics_available:
                venue_metrics["liquidity_metrics"] = self.calculate_liquidity_metrics(df)
            else:
                # Create stub for incomplete schema
                venue_metrics["liquidity_metrics"] = {
                    "liquidity_score": np.nan,
                    "depth_imbalance": np.nan,
                    "liquidity_volatility": np.nan,
                    "market_impact": np.nan,
                    "liquidity_ratio": np.nan,
                }

            results["metrics"][venue] = venue_metrics

        # Calculate cross-venue metrics
        if enhanced_metrics_available:
            results["cross_venue"] = {
                "lead_lag": self.calculate_lead_lag(data),
                "infoshare": self.calculate_infoshare(data),
                "leadership_shares": self.calculate_leadership_shares(data),
            }
        else:
            # Create stub for incomplete schema
            results["cross_venue"] = {
                "lead_lag": {},
                "infoshare": {},
                "leadership_shares": {
                    "volume_weighted": {},
                    "price_impact": {},
                    "information_leadership": {},
                    "venue_specialization": {},
                },
            }

        # Add schema validation details
        results["schema_validation"] = schema_result

        return results

    def store_results(self, results: Dict[str, Any], output_path: str):
        """Store results to S3"""
        try:
            # Convert to JSON-serializable format
            json_results = json.dumps(results, indent=2, default=str)

            # Upload to S3
            self.s3.put_object(
                Bucket=self.bucket,
                Key=output_path,
                Body=json_results,
                ContentType="application/json",
            )

            logger.info(f"Stored results to s3://{self.bucket}/{output_path}")

        except Exception as e:
            logger.error(f"Failed to store results: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description="Continuous Variable Measurement")
    parser.add_argument("--symbol", required=True, help="Trading symbol (e.g., BTC-USD)")
    parser.add_argument("--date", required=True, help="Date (YYYYMMDD)")
    parser.add_argument("--time-range", required=True, help="Time range (e.g., 1300-1400)")
    parser.add_argument("--output-path", required=True, help="S3 output path")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket")
    parser.add_argument("--prefix", default="snapshots", help="S3 prefix")

    args = parser.parse_args()

    # Initialize measurement system
    measurement = ContinuousMeasurement(bucket=args.bucket, prefix=args.prefix)

    try:
        # Process window
        results = measurement.process_window(args.symbol, args.date, args.time_range)

        if results:
            # Store results
            measurement.store_results(results, args.output_path)
            logger.info("Continuous measurement completed successfully")
        else:
            logger.error("No results generated")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Continuous measurement failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
