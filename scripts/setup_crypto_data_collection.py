#!/usr/bin/env python3
"""
Crypto Data Collection Setup Script

This script sets up the infrastructure for collecting live crypto market data
for crypto moment validation in Phase-4.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_crypto_data_schema():
    """Create schema for crypto market data collection"""

    print("Creating Crypto Data Collection Schema...")

    schema = {
        "data_types": {
            "orderbook": {
                "description": "Order book data with bid/ask prices and volumes",
                "fields": [
                    "timestamp",
                    "exchange",
                    "symbol",
                    "bid_price",
                    "ask_price",
                    "bid_volume",
                    "ask_volume",
                    "spread",
                    "mid_price",
                ],
                "frequency": "1_second",
                "retention": "30_days",
            },
            "trades": {
                "description": "Trade execution data",
                "fields": [
                    "timestamp",
                    "exchange",
                    "symbol",
                    "price",
                    "volume",
                    "side",
                    "trade_id",
                    "order_id",
                ],
                "frequency": "real_time",
                "retention": "7_days",
            },
            "spreads": {
                "description": "Spread analysis data",
                "fields": [
                    "timestamp",
                    "exchange",
                    "symbol",
                    "spread_bps",
                    "spread_abs",
                    "bid_price",
                    "ask_price",
                    "volume_weighted_spread",
                ],
                "frequency": "1_second",
                "retention": "30_days",
            },
            "volumes": {
                "description": "Volume and liquidity data",
                "fields": [
                    "timestamp",
                    "exchange",
                    "symbol",
                    "volume_24h",
                    "volume_1h",
                    "liquidity_score",
                    "market_share",
                ],
                "frequency": "1_minute",
                "retention": "90_days",
            },
        },
        "exchanges": [
            {
                "name": "binance",
                "display_name": "Binance",
                "api_endpoint": "https://api.binance.com",
                "websocket_endpoint": "wss://stream.binance.com:9443/ws",
                "supported_pairs": ["BTCUSDT", "ETHUSDT", "ADAUSDT"],
                "rate_limits": {"requests_per_minute": 1200, "weight_per_minute": 6000},
            },
            {
                "name": "coinbase",
                "display_name": "Coinbase Pro",
                "api_endpoint": "https://api.pro.coinbase.com",
                "websocket_endpoint": "wss://ws-feed.pro.coinbase.com",
                "supported_pairs": ["BTC-USD", "ETH-USD", "ADA-USD"],
                "rate_limits": {"requests_per_minute": 10, "weight_per_minute": 100},
            },
            {
                "name": "kraken",
                "display_name": "Kraken",
                "api_endpoint": "https://api.kraken.com",
                "websocket_endpoint": "wss://ws.kraken.com",
                "supported_pairs": ["XBTUSD", "ETHUSD", "ADAUSD"],
                "rate_limits": {"requests_per_minute": 1, "weight_per_minute": 10},
            },
        ],
        "crypto_pairs": [
            {
                "symbol": "BTC/USD",
                "base": "BTC",
                "quote": "USD",
                "exchanges": ["binance", "coinbase", "kraken"],
                "priority": "high",
            },
            {
                "symbol": "ETH/USD",
                "base": "ETH",
                "quote": "USD",
                "exchanges": ["binance", "coinbase", "kraken"],
                "priority": "high",
            },
            {
                "symbol": "ADA/USD",
                "base": "ADA",
                "quote": "USD",
                "exchanges": ["binance", "coinbase", "kraken"],
                "priority": "medium",
            },
        ],
        "crypto_moments": {
            "lead_lag": {
                "description": "Lead-lag relationships between exchanges",
                "parameters": {"window_size": 30, "min_correlation": 0.3, "max_lag": 5},
            },
            "mirroring": {
                "description": "Order book mirroring patterns",
                "parameters": {"similarity_threshold": 0.7, "depth_levels": 10, "time_window": 60},
            },
            "spread_floors": {
                "description": "Spread floor detection and dwell times",
                "parameters": {
                    "floor_threshold": 0.5,
                    "min_dwell_time": 30,
                    "detection_window": 300,
                },
            },
            "undercut_initiation": {
                "description": "Undercut initiation patterns",
                "parameters": {
                    "undercut_threshold": 0.1,
                    "response_time_window": 10,
                    "min_volume": 1000,
                },
            },
            "mev_coordination": {
                "description": "MEV coordination detection",
                "parameters": {
                    "mev_threshold": 0.2,
                    "coordination_window": 5,
                    "min_transactions": 10,
                },
            },
        },
    }

    # Save schema to file
    schema_file = Path("artifacts/crypto_data_schema.json")
    schema_file.parent.mkdir(parents=True, exist_ok=True)

    with open(schema_file, "w") as f:
        json.dump(schema, f, indent=2)

    print(f"   ✅ Crypto data schema created: {schema_file}")
    return schema


def create_mock_crypto_data():
    """Create mock crypto data for testing and validation"""

    print("\nCreating Mock Crypto Data for Testing...")

    # Generate mock data for the last 2 weeks
    end_time = datetime.now()
    start_time = end_time - timedelta(days=14)

    # Create time series
    timestamps = pd.date_range(start_time, end_time, freq="1min")

    # Generate mock data for each exchange and pair
    exchanges = ["binance", "coinbase", "kraken"]
    pairs = ["BTC/USD", "ETH/USD", "ADA/USD"]

    mock_data = []

    for exchange in exchanges:
        for pair in pairs:
            # Generate base price with trend and volatility
            base_price = 50000 if "BTC" in pair else (3000 if "ETH" in pair else 0.5)
            price_trend = np.cumsum(np.random.normal(0, base_price * 0.001, len(timestamps)))
            prices = base_price + price_trend

            # Add exchange-specific variations
            exchange_multiplier = 1.0
            if exchange == "coinbase":
                exchange_multiplier = 1.001  # Slightly higher prices
            elif exchange == "kraken":
                exchange_multiplier = 0.999  # Slightly lower prices

            prices *= exchange_multiplier

            # Generate spreads (bid-ask)
            spreads = np.random.uniform(0.5, 2.0, len(timestamps))  # 0.5-2.0 bps

            for i, timestamp in enumerate(timestamps):
                mid_price = prices[i]
                spread = spreads[i]

                # Add some coordination patterns (higher correlation during certain periods)
                coordination_strength = (
                    0.3 if i % 100 < 20 else 0.1
                )  # 20% of time has higher coordination

                bid_price = mid_price - (spread / 2) * mid_price / 10000
                ask_price = mid_price + (spread / 2) * mid_price / 10000

                # Add coordination effects
                if coordination_strength > 0.2:
                    # During coordination periods, prices are more similar across exchanges
                    coordination_factor = 1 + coordination_strength * 0.1
                    bid_price *= coordination_factor
                    ask_price *= coordination_factor

                # Generate volumes
                base_volume = np.random.exponential(1000)
                bid_volume = base_volume * np.random.uniform(0.8, 1.2)
                ask_volume = base_volume * np.random.uniform(0.8, 1.2)

                mock_data.append(
                    {
                        "timestamp": timestamp,
                        "exchange": exchange,
                        "symbol": pair,
                        "bid_price": round(bid_price, 2),
                        "ask_price": round(ask_price, 2),
                        "bid_volume": round(bid_volume, 2),
                        "ask_volume": round(ask_volume, 2),
                        "spread": round(spread, 2),
                        "mid_price": round(mid_price, 2),
                        "coordination_strength": round(coordination_strength, 2),
                    }
                )

    # Convert to DataFrame
    df = pd.DataFrame(mock_data)

    # Save to file
    data_file = Path("artifacts/mock_crypto_data.csv")
    df.to_csv(data_file, index=False)

    print(f"   ✅ Mock crypto data created: {data_file}")
    print(f"   Records: {len(df):,}")
    print(f"   Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"   Exchanges: {df['exchange'].nunique()}")
    print(f"   Pairs: {df['symbol'].nunique()}")

    return df


def create_crypto_moment_validation_script():
    """Create script for validating crypto moments with real data"""

    print("\nCreating Crypto Moment Validation Script...")

    validation_script = '''#!/usr/bin/env python3
"""
Crypto Moment Validation Script

This script validates crypto moments against real market data
and compares results with synthetic validations.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any

from acd.vmm.crypto_moments import CryptoMomentCalculator, CryptoMomentConfig
from acd.validation.lead_lag import LeadLagValidator, LeadLagConfig
from acd.validation.mirroring import MirroringValidator, MirroringConfig


def load_crypto_data(data_file: str) -> pd.DataFrame:
    """Load crypto data from file"""
    
    print(f"Loading crypto data from: {data_file}")
    
    df = pd.read_csv(data_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print(f"   Records: {len(df):,}")
    print(f"   Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"   Exchanges: {df['exchange'].nunique()}")
    print(f"   Pairs: {df['symbol'].nunique()}")
    
    return df


def prepare_data_for_analysis(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Prepare data for crypto moment analysis"""
    
    print("Preparing data for crypto moment analysis...")
    
    # Pivot data for each pair
    prepared_data = {}
    
    for pair in df['symbol'].unique():
        pair_data = df[df['symbol'] == pair].copy()
        
        # Create wide format for analysis
        pivot_data = pair_data.pivot_table(
            index='timestamp',
            columns='exchange',
            values=['mid_price', 'spread', 'bid_volume', 'ask_volume'],
            aggfunc='mean'
        ).fillna(method='ffill')
        
        prepared_data[pair] = pivot_data
        
        print(f"   {pair}: {len(pivot_data)} timestamps, {len(pivot_data.columns)} columns")
    
    return prepared_data


def validate_lead_lag_moments(data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Validate lead-lag moments"""
    
    print("Validating lead-lag moments...")
    
    config = LeadLagConfig(window_size=30, min_samples=50)
    validator = LeadLagValidator(config)
    
    results = {}
    
    for pair, pair_data in data.items():
        print(f"   Analyzing {pair}...")
        
        try:
            # Extract price columns
            price_columns = [col for col in pair_data.columns if 'mid_price' in col]
            price_data = pair_data[price_columns]
            
            result = validator.analyze_lead_lag(price_data)
            
            results[pair] = {
                'switching_entropy': result.switching_entropy,
                'avg_granger_p': result.avg_granger_p,
                'n_windows': result.n_windows,
                'n_exchanges': result.n_exchanges
            }
            
            print(f"     Switching entropy: {result.switching_entropy:.3f}")
            print(f"     Avg Granger p-value: {result.avg_granger_p:.3f}")
            
        except Exception as e:
            print(f"     Error analyzing {pair}: {e}")
            results[pair] = {'error': str(e)}
    
    return results


def validate_mirroring_moments(data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Validate mirroring moments"""
    
    print("Validating mirroring moments...")
    
    config = MirroringConfig(threshold=0.7, min_samples=50)
    validator = MirroringValidator(config)
    
    results = {}
    
    for pair, pair_data in data.items():
        print(f"   Analyzing {pair}...")
        
        try:
            # Extract price columns
            price_columns = [col for col in pair_data.columns if 'mid_price' in col]
            price_data = pair_data[price_columns]
            
            result = validator.analyze_mirroring(price_data)
            
            results[pair] = {
                'mirroring_ratio': result.mirroring_ratio,
                'coordination_score': result.coordination_score,
                'avg_cosine_similarity': result.avg_cosine_similarity,
                'n_windows': result.n_windows,
                'n_exchanges': result.n_exchanges
            }
            
            print(f"     Mirroring ratio: {result.mirroring_ratio:.3f}")
            print(f"     Coordination score: {result.coordination_score:.3f}")
            
        except Exception as e:
            print(f"     Error analyzing {pair}: {e}")
            results[pair] = {'error': str(e)}
    
    return results


def validate_crypto_moments(data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Validate crypto moments using CryptoMomentCalculator"""
    
    print("Validating crypto moments...")
    
    config = CryptoMomentConfig()
    calculator = CryptoMomentCalculator(config)
    
    results = {}
    
    for pair, pair_data in data.items():
        print(f"   Analyzing {pair}...")
        
        try:
            # Calculate crypto moments
            moments = calculator.calculate_moments(pair_data)
            
            results[pair] = {
                'lead_lag_betas': moments.lead_lag_betas.tolist(),
                'mirroring_ratios': moments.mirroring_ratios.tolist(),
                'spread_floor_frequency': moments.spread_floor_frequency.tolist(),
                'undercut_initiation_rate': moments.undercut_initiation_rate.tolist(),
                'mev_coordination_score': moments.mev_coordination_score.tolist()
            }
            
            print(f"     Lead-lag betas: {np.mean(moments.lead_lag_betas):.3f}")
            print(f"     Mirroring ratios: {np.mean(moments.mirroring_ratios):.3f}")
            print(f"     Spread floor frequency: {np.mean(moments.spread_floor_frequency):.3f}")
            
        except Exception as e:
            print(f"     Error analyzing {pair}: {e}")
            results[pair] = {'error': str(e)}
    
    return results


def compare_with_synthetic_results(real_results: Dict[str, Any], synthetic_results: Dict[str, Any]) -> Dict[str, Any]:
    """Compare real data results with synthetic validation results"""
    
    print("Comparing with synthetic validation results...")
    
    comparison = {}
    
    for pair in real_results.keys():
        if pair in synthetic_results and 'error' not in real_results[pair]:
            real = real_results[pair]
            synthetic = synthetic_results[pair]
            
            # Calculate consistency metrics
            consistency_metrics = {}
            
            for metric in ['switching_entropy', 'mirroring_ratio', 'coordination_score']:
                if metric in real and metric in synthetic:
                    real_val = real[metric]
                    synthetic_val = synthetic[metric]
                    
                    # Calculate relative difference
                    if synthetic_val != 0:
                        relative_diff = abs(real_val - synthetic_val) / abs(synthetic_val)
                        consistency_metrics[metric] = {
                            'real': real_val,
                            'synthetic': synthetic_val,
                            'relative_difference': relative_diff,
                            'consistent': relative_diff < 0.2  # 20% tolerance
                        }
            
            comparison[pair] = consistency_metrics
            
            # Summary
            consistent_metrics = sum(1 for m in consistency_metrics.values() if m['consistent'])
            total_metrics = len(consistency_metrics)
            
            print(f"   {pair}: {consistent_metrics}/{total_metrics} metrics consistent")
    
    return comparison


def main():
    """Main validation function"""
    
    print("🚀 Crypto Moment Validation")
    print("=" * 50)
    
    # Load data
    data_file = "artifacts/mock_crypto_data.csv"
    if not Path(data_file).exists():
        print(f"❌ Data file not found: {data_file}")
        print("Please run setup_crypto_data_collection.py first")
        return False
    
    df = load_crypto_data(data_file)
    prepared_data = prepare_data_for_analysis(df)
    
    # Validate moments
    lead_lag_results = validate_lead_lag_moments(prepared_data)
    mirroring_results = validate_mirroring_moments(prepared_data)
    crypto_moment_results = validate_crypto_moments(prepared_data)
    
    # Save results
    results = {
        'timestamp': datetime.now().isoformat(),
        'data_file': data_file,
        'lead_lag_results': lead_lag_results,
        'mirroring_results': mirroring_results,
        'crypto_moment_results': crypto_moment_results
    }
    
    results_file = Path("artifacts/crypto_validation_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\\n✅ Validation results saved: {results_file}")
    
    # Summary
    successful_pairs = sum(1 for r in lead_lag_results.values() if 'error' not in r)
    total_pairs = len(lead_lag_results)
    
    print(f"\\n📊 Validation Summary:")
    print(f"   Total pairs: {total_pairs}")
    print(f"   Successful validations: {successful_pairs}")
    print(f"   Success rate: {successful_pairs/total_pairs*100:.1f}%")
    
    return successful_pairs == total_pairs


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
'''

    # Save validation script
    script_file = Path("scripts/validate_crypto_moments.py")
    with open(script_file, "w") as f:
        f.write(validation_script)

    print(f"   ✅ Crypto moment validation script created: {script_file}")
    return script_file


def create_data_collection_infrastructure():
    """Create infrastructure for live data collection"""

    print("\nCreating Data Collection Infrastructure...")

    # Create data collection configuration
    config = {
        "data_collection": {
            "enabled": False,  # Will be enabled when live data sources are available
            "sources": [
                {
                    "name": "binance_websocket",
                    "type": "websocket",
                    "endpoint": "wss://stream.binance.com:9443/ws",
                    "pairs": ["btcusdt", "ethusdt"],
                    "data_types": ["orderbook", "trades"],
                },
                {
                    "name": "coinbase_websocket",
                    "type": "websocket",
                    "endpoint": "wss://ws-feed.pro.coinbase.com",
                    "pairs": ["BTC-USD", "ETH-USD"],
                    "data_types": ["orderbook", "trades"],
                },
            ],
            "storage": {
                "type": "csv",
                "directory": "artifacts/crypto_data",
                "retention_days": 30,
                "compression": "gzip",
            },
            "processing": {
                "batch_size": 1000,
                "processing_interval": 60,  # seconds
                "real_time_analysis": True,
            },
        },
        "monitoring": {
            "enabled": True,
            "metrics": ["data_quality_score", "collection_latency", "error_rate", "throughput"],
            "alerts": [
                {"metric": "error_rate", "threshold": 0.05, "action": "email_alert"},
                {"metric": "collection_latency", "threshold": 5.0, "action": "log_warning"},
            ],
        },
    }

    # Save configuration
    config_file = Path("artifacts/crypto_data_collection_config.json")
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    print(f"   ✅ Data collection configuration created: {config_file}")

    # Create data directory
    data_dir = Path("artifacts/crypto_data")
    data_dir.mkdir(parents=True, exist_ok=True)

    print(f"   ✅ Data directory created: {data_dir}")

    return config


def main():
    """Main setup function"""

    print("🚀 Crypto Data Collection Setup")
    print("=" * 50)

    try:
        # Create crypto data schema
        schema = create_crypto_data_schema()

        # Create mock crypto data
        mock_data = create_mock_crypto_data()

        # Create validation script
        validation_script = create_crypto_moment_validation_script()

        # Create data collection infrastructure
        config = create_data_collection_infrastructure()

        print("\n" + "=" * 50)
        print("🎉 Crypto Data Collection Setup Completed!")

        print(f"\n📊 Setup Summary:")
        print(f"   ✅ Data schema created")
        print(f"   ✅ Mock data generated: {len(mock_data):,} records")
        print(f"   ✅ Validation script created")
        print(f"   ✅ Collection infrastructure configured")

        print(f"\n📁 Files Created:")
        print(f"   - artifacts/crypto_data_schema.json")
        print(f"   - artifacts/mock_crypto_data.csv")
        print(f"   - scripts/validate_crypto_moments.py")
        print(f"   - artifacts/crypto_data_collection_config.json")
        print(f"   - artifacts/crypto_data/ (directory)")

        print(f"\n🔍 Next Steps:")
        print(f"   1. Run validation script: python scripts/validate_crypto_moments.py")
        print(f"   2. Set up live data sources when available")
        print(f"   3. Enable data collection in configuration")
        print(f"   4. Begin crypto moment validation with real data")

        return True

    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
