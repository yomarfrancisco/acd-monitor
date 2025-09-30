#!/usr/bin/env python3
"""
Prepare variables for Wave-2 econometric tests (Econometric Deepening)

Tests 6-10:
6. Event Studies on Exogenous Shocks
7. Granger Causality Networks
8. Cointegration & Error Correction Models
9. Markov Switching Regimes
10. Variance Decomposition (Structural VAR)
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class Wave2VariablePreparer:
    """Prepare variables for Wave-2 econometric tests."""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.output_dir = f"analysis/wave2/{symbol.replace('-', '_').lower()}"
        self.data_dir = f"data/derived/{symbol.replace('-', '_').lower()}"
        
        # Create output directories
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        self.panel_data = None
        self.variables = {}
        
    def prepare_all_variables(self):
        """Prepare all Wave-2 variables."""
        print(f"🔧 Wave-2 Variable Preparation for {self.symbol}")
        print("=" * 50)
        
        # Load aligned panel data
        self._load_aligned_panel()
        
        if self.panel_data is None or self.panel_data.empty:
            print("❌ No aligned panel data found")
            return
        
        print(f"📊 Loaded aligned panel: {len(self.panel_data)} observations")
        
        # Prepare variables for each test
        self._prepare_event_study_variables()
        self._prepare_granger_causality_variables()
        self._prepare_cointegration_variables()
        self._prepare_markov_switching_variables()
        self._prepare_svar_variables()
        
        # Save all variables
        self._save_variables()
        
        print(f"✅ Wave-2 variable preparation complete")
        print(f"📁 Results saved to {self.output_dir}")
    
    def _load_aligned_panel(self):
        """Load aligned panel data."""
        panel_file = f"{self.data_dir}/panel_1s_inner.parquet"
        
        if not os.path.exists(panel_file):
            print(f"❌ Panel file not found: {panel_file}")
            return
        
        self.panel_data = pd.read_parquet(panel_file)
        print(f"📥 Loaded panel from {panel_file}")
    
    def _prepare_event_study_variables(self):
        """Test 6: Event Studies on Exogenous Shocks variables."""
        print("\n📅 Preparing Event Study variables...")
        
        # Identify potential shock events
        shock_events = self._identify_shock_events()
        
        # Create event study dataset
        event_data = []
        for event in shock_events:
            event_window = self._create_event_window(event)
            if event_window is not None:
                event_data.append(event_window)
        
        # Save event study data
        if event_data:
            event_df = pd.concat(event_data, ignore_index=True)
            event_df.to_parquet(f"{self.data_dir}/event_study_data.parquet")
            
            self.variables['event_study'] = {
                'events_identified': len(shock_events),
                'event_windows': len(event_data),
                'data_file': f"{self.data_dir}/event_study_data.parquet"
            }
            
            print(f"  ✅ Event study variables prepared")
            print(f"    Events identified: {len(shock_events)}")
            print(f"    Event windows: {len(event_data)}")
        else:
            print("  ⚠️ No shock events identified")
            self.variables['event_study'] = {'events_identified': 0}
    
    def _identify_shock_events(self) -> List[Dict]:
        """Identify potential shock events in the data."""
        shock_events = []
        
        # Large price movements (top 1% of absolute returns)
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            if mid_col in self.panel_data.columns:
                prices = self.panel_data[mid_col].dropna()
                if len(prices) > 100:
                    returns = prices.pct_change().dropna()
                    large_moves = returns[abs(returns) > returns.quantile(0.99)]
                    
                    for timestamp, return_val in large_moves.items():
                        shock_events.append({
                            'timestamp': timestamp,
                            'type': 'large_price_move',
                            'venue': venue,
                            'magnitude': abs(return_val),
                            'direction': 'positive' if return_val > 0 else 'negative'
                        })
        
        # Spread anomalies (unusually wide or narrow spreads)
        for venue in self.venues:
            spread_col = f"{venue}_spread"
            if spread_col in self.panel_data.columns:
                spreads = self.panel_data[spread_col].dropna()
                if len(spreads) > 100:
                    # Wide spreads (top 1%)
                    wide_spreads = spreads[spreads > spreads.quantile(0.99)]
                    for timestamp, spread_val in wide_spreads.items():
                        shock_events.append({
                            'timestamp': timestamp,
                            'type': 'wide_spread',
                            'venue': venue,
                            'magnitude': spread_val
                        })
                    
                    # Narrow spreads (bottom 1%)
                    narrow_spreads = spreads[spreads < spreads.quantile(0.01)]
                    for timestamp, spread_val in narrow_spreads.items():
                        shock_events.append({
                            'timestamp': timestamp,
                            'type': 'narrow_spread',
                            'venue': venue,
                            'magnitude': spread_val
                        })
        
        # Remove duplicates and sort by timestamp
        unique_events = []
        seen_timestamps = set()
        
        for event in shock_events:
            if event['timestamp'] not in seen_timestamps:
                unique_events.append(event)
                seen_timestamps.add(event['timestamp'])
        
        return sorted(unique_events, key=lambda x: x['timestamp'])
    
    def _create_event_window(self, event: Dict) -> Optional[pd.DataFrame]:
        """Create event window data around a shock."""
        event_time = event['timestamp']
        
        # Define event window (±30 minutes)
        window_start = event_time - pd.Timedelta(minutes=30)
        window_end = event_time + pd.Timedelta(minutes=30)
        
        # Extract window data
        window_data = self.panel_data[
            (self.panel_data.index >= window_start) & 
            (self.panel_data.index <= window_end)
        ].copy()
        
        if len(window_data) < 10:  # Need sufficient data
            return None
        
        # Add event metadata
        window_data['event_timestamp'] = event_time
        window_data['event_type'] = event['type']
        window_data['event_venue'] = event['venue']
        window_data['event_magnitude'] = event['magnitude']
        window_data['time_to_event'] = (window_data.index - event_time).total_seconds()
        
        return window_data
    
    def _prepare_granger_causality_variables(self):
        """Test 7: Granger Causality Networks variables."""
        print("\n🔗 Preparing Granger Causality variables...")
        
        # Get aligned returns for all venues
        venue_returns = {}
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            if mid_col in self.panel_data.columns:
                prices = self.panel_data[mid_col].dropna()
                if len(prices) > 100:
                    returns = prices.pct_change().dropna()
                    if len(returns) > 50:
                        venue_returns[venue] = returns
        
        if len(venue_returns) < 2:
            print("  ❌ Insufficient venue data for Granger causality")
            self.variables['granger_causality'] = {'venues_available': 0}
            return
        
        # Align returns to common time index
        common_idx = None
        for venue, returns in venue_returns.items():
            if common_idx is None:
                common_idx = returns.index
            else:
                common_idx = common_idx.intersection(returns.index)
        
        if len(common_idx) < 100:
            print("  ❌ Insufficient common observations")
            self.variables['granger_causality'] = {'venues_available': 0}
            return
        
        # Create aligned returns matrix
        aligned_returns = {}
        for venue, returns in venue_returns.items():
            aligned_returns[venue] = returns.loc[common_idx]
        
        returns_df = pd.DataFrame(aligned_returns)
        returns_df = returns_df.dropna()
        
        if len(returns_df) < 100:
            print("  ❌ Insufficient data after alignment")
            self.variables['granger_causality'] = {'venues_available': 0}
            return
        
        # Create lagged variables for Granger tests
        max_lags = 5  # Test up to 5 lags
        granger_data = returns_df.copy()
        
        for venue in returns_df.columns:
            for lag in range(1, max_lags + 1):
                granger_data[f"{venue}_lag_{lag}"] = returns_df[venue].shift(lag)
        
        # Save Granger causality data
        granger_data.to_parquet(f"{self.data_dir}/granger_causality_data.parquet")
        
        self.variables['granger_causality'] = {
            'venues_available': len(returns_df.columns),
            'observations': len(granger_data),
            'max_lags': max_lags,
            'data_file': f"{self.data_dir}/granger_causality_data.parquet"
        }
        
        print(f"  ✅ Granger causality variables prepared")
        print(f"    Venues: {len(returns_df.columns)}")
        print(f"    Observations: {len(granger_data)}")
        print(f"    Max lags: {max_lags}")
    
    def _prepare_cointegration_variables(self):
        """Test 8: Cointegration & Error Correction Models variables."""
        print("\n🔗 Preparing Cointegration variables...")
        
        # Get aligned prices for all venues
        venue_prices = {}
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            if mid_col in self.panel_data.columns:
                prices = self.panel_data[mid_col].dropna()
                if len(prices) > 100:
                    venue_prices[venue] = prices
        
        if len(venue_prices) < 2:
            print("  ❌ Insufficient venue data for cointegration")
            self.variables['cointegration'] = {'venues_available': 0}
            return
        
        # Align prices to common time index
        common_idx = None
        for venue, prices in venue_prices.items():
            if common_idx is None:
                common_idx = prices.index
            else:
                common_idx = common_idx.intersection(prices.index)
        
        if len(common_idx) < 100:
            print("  ❌ Insufficient common observations")
            self.variables['cointegration'] = {'venues_available': 0}
            return
        
        # Create aligned price matrix
        aligned_prices = {}
        for venue, prices in venue_prices.items():
            aligned_prices[venue] = prices.loc[common_idx]
        
        prices_df = pd.DataFrame(aligned_prices)
        prices_df = prices_df.dropna()
        
        if len(prices_df) < 100:
            print("  ❌ Insufficient data after alignment")
            self.variables['cointegration'] = {'venues_available': 0}
            return
        
        # Create cointegration variables
        cointegration_data = prices_df.copy()
        
        # Add first differences (for stationarity)
        for venue in prices_df.columns:
            cointegration_data[f"{venue}_diff"] = prices_df[venue].diff()
        
        # Add error correction terms (price differences)
        for i, venue1 in enumerate(prices_df.columns):
            for venue2 in prices_df.columns[i+1:]:
                cointegration_data[f"ec_{venue1}_{venue2}"] = prices_df[venue1] - prices_df[venue2]
        
        # Save cointegration data
        cointegration_data.to_parquet(f"{self.data_dir}/cointegration_data.parquet")
        
        self.variables['cointegration'] = {
            'venues_available': len(prices_df.columns),
            'observations': len(cointegration_data),
            'price_series': list(prices_df.columns),
            'data_file': f"{self.data_dir}/cointegration_data.parquet"
        }
        
        print(f"  ✅ Cointegration variables prepared")
        print(f"    Venues: {len(prices_df.columns)}")
        print(f"    Observations: {len(cointegration_data)}")
    
    def _prepare_markov_switching_variables(self):
        """Test 9: Markov Switching Regimes variables."""
        print("\n🔄 Preparing Markov Switching variables...")
        
        # Get aligned spreads and returns for all venues
        venue_data = {}
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            spread_col = f"{venue}_spread"
            
            if mid_col in self.panel_data.columns and spread_col in self.panel_data.columns:
                prices = self.panel_data[mid_col].dropna()
                spreads = self.panel_data[spread_col].dropna()
                
                if len(prices) > 100 and len(spreads) > 100:
                    returns = prices.pct_change().dropna()
                    if len(returns) > 50:
                        venue_data[venue] = {
                            'returns': returns,
                            'spreads': spreads,
                            'prices': prices
                        }
        
        if len(venue_data) < 2:
            print("  ❌ Insufficient venue data for Markov switching")
            self.variables['markov_switching'] = {'venues_available': 0}
            return
        
        # Align all series to common time index
        common_idx = None
        for venue, data in venue_data.items():
            venue_idx = data['returns'].index.intersection(data['spreads'].index)
            if common_idx is None:
                common_idx = venue_idx
            else:
                common_idx = common_idx.intersection(venue_idx)
        
        if len(common_idx) < 100:
            print("  ❌ Insufficient common observations")
            self.variables['markov_switching'] = {'venues_available': 0}
            return
        
        # Create aligned data matrix
        markov_data = pd.DataFrame(index=common_idx)
        
        for venue, data in venue_data.items():
            aligned_returns = data['returns'].loc[common_idx]
            aligned_spreads = data['spreads'].loc[common_idx]
            
            markov_data[f"{venue}_returns"] = aligned_returns
            markov_data[f"{venue}_spreads"] = aligned_spreads
            markov_data[f"{venue}_spread_changes"] = aligned_spreads.pct_change()
        
        markov_data = markov_data.dropna()
        
        if len(markov_data) < 100:
            print("  ❌ Insufficient data after alignment")
            self.variables['markov_switching'] = {'venues_available': 0}
            return
        
        # Add regime indicators (rolling statistics)
        window_size = 60  # 1-minute windows
        for venue in venue_data.keys():
            returns_col = f"{venue}_returns"
            spreads_col = f"{venue}_spreads"
            
            if returns_col in markov_data.columns and spreads_col in markov_data.columns:
                # Rolling volatility
                markov_data[f"{venue}_volatility"] = markov_data[returns_col].rolling(window_size).std()
                
                # Rolling spread volatility
                markov_data[f"{venue}_spread_volatility"] = markov_data[f"{venue}_spread_changes"].rolling(window_size).std()
                
                # Rolling correlation between returns and spread changes
                markov_data[f"{venue}_return_spread_corr"] = markov_data[returns_col].rolling(window_size).corr(markov_data[f"{venue}_spread_changes"])
        
        # Save Markov switching data
        markov_data.to_parquet(f"{self.data_dir}/markov_switching_data.parquet")
        
        self.variables['markov_switching'] = {
            'venues_available': len(venue_data),
            'observations': len(markov_data),
            'window_size': window_size,
            'data_file': f"{self.data_dir}/markov_switching_data.parquet"
        }
        
        print(f"  ✅ Markov switching variables prepared")
        print(f"    Venues: {len(venue_data)}")
        print(f"    Observations: {len(markov_data)}")
        print(f"    Window size: {window_size}")
    
    def _prepare_svar_variables(self):
        """Test 10: Variance Decomposition (Structural VAR) variables."""
        print("\n📊 Preparing SVAR variables...")
        
        # Get aligned returns for all venues
        venue_returns = {}
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            if mid_col in self.panel_data.columns:
                prices = self.panel_data[mid_col].dropna()
                if len(prices) > 100:
                    returns = prices.pct_change().dropna()
                    if len(returns) > 50:
                        venue_returns[venue] = returns
        
        if len(venue_returns) < 3:
            print("  ❌ Need at least 3 venues for SVAR")
            self.variables['svar'] = {'venues_available': 0}
            return
        
        # Align returns to common time index
        common_idx = None
        for venue, returns in venue_returns.items():
            if common_idx is None:
                common_idx = returns.index
            else:
                common_idx = common_idx.intersection(returns.index)
        
        if len(common_idx) < 100:
            print("  ❌ Insufficient common observations")
            self.variables['svar'] = {'venues_available': 0}
            return
        
        # Create aligned returns matrix
        aligned_returns = {}
        for venue, returns in venue_returns.items():
            aligned_returns[venue] = returns.loc[common_idx]
        
        returns_df = pd.DataFrame(aligned_returns)
        returns_df = returns_df.dropna()
        
        if len(returns_df) < 100:
            print("  ❌ Insufficient data after alignment")
            self.variables['svar'] = {'venues_available': 0}
            return
        
        # Create SVAR variables
        svar_data = returns_df.copy()
        
        # Add exogenous variables (market-wide indicators)
        svar_data['market_volatility'] = returns_df.std(axis=1)
        svar_data['market_skewness'] = returns_df.skew(axis=1)
        svar_data['market_kurtosis'] = returns_df.kurtosis(axis=1)
        
        # Add lagged variables
        max_lags = 3
        for venue in returns_df.columns:
            for lag in range(1, max_lags + 1):
                svar_data[f"{venue}_lag_{lag}"] = returns_df[venue].shift(lag)
        
        # Add cross-venue indicators
        for venue in returns_df.columns:
            other_venues = [v for v in returns_df.columns if v != venue]
            svar_data[f"{venue}_others_mean"] = returns_df[other_venues].mean(axis=1)
            svar_data[f"{venue}_others_std"] = returns_df[other_venues].std(axis=1)
        
        # Save SVAR data
        svar_data.to_parquet(f"{self.data_dir}/svar_data.parquet")
        
        self.variables['svar'] = {
            'venues_available': len(returns_df.columns),
            'observations': len(svar_data),
            'max_lags': max_lags,
            'exogenous_vars': ['market_volatility', 'market_skewness', 'market_kurtosis'],
            'data_file': f"{self.data_dir}/svar_data.parquet"
        }
        
        print(f"  ✅ SVAR variables prepared")
        print(f"    Venues: {len(returns_df.columns)}")
        print(f"    Observations: {len(svar_data)}")
        print(f"    Max lags: {max_lags}")
    
    def _save_variables(self):
        """Save all prepared variables."""
        variables_data = {
            'symbol': self.symbol,
            'timestamp': datetime.utcnow().isoformat(),
            'panel_observations': len(self.panel_data) if self.panel_data is not None else 0,
            'variables': self.variables
        }
        
        with open(f'{self.output_dir}/wave2_variables.json', 'w') as f:
            json.dump(variables_data, f, indent=2, default=str)
        
        # Create summary report
        self._create_summary_report()
    
    def _create_summary_report(self):
        """Create summary report of prepared variables."""
        report = f"""# Wave-2 Variable Preparation Summary - {self.symbol}

## Overview
Successfully prepared variables for Wave-2 econometric deepening tests.

**Analysis Date**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
**Symbol**: {self.symbol}
**Panel Observations**: {len(self.panel_data) if self.panel_data is not None else 0}

## Variables Prepared

### 6. Event Studies on Exogenous Shocks
- **Events Identified**: {self.variables.get('event_study', {}).get('events_identified', 0)}
- **Event Windows**: {self.variables.get('event_study', {}).get('event_windows', 0)}
- **Data File**: {self.variables.get('event_study', {}).get('data_file', 'N/A')}

### 7. Granger Causality Networks
- **Venues Available**: {self.variables.get('granger_causality', {}).get('venues_available', 0)}
- **Observations**: {self.variables.get('granger_causality', {}).get('observations', 0)}
- **Max Lags**: {self.variables.get('granger_causality', {}).get('max_lags', 0)}

### 8. Cointegration & Error Correction Models
- **Venues Available**: {self.variables.get('cointegration', {}).get('venues_available', 0)}
- **Observations**: {self.variables.get('cointegration', {}).get('observations', 0)}
- **Price Series**: {self.variables.get('cointegration', {}).get('price_series', [])}

### 9. Markov Switching Regimes
- **Venues Available**: {self.variables.get('markov_switching', {}).get('venues_available', 0)}
- **Observations**: {self.variables.get('markov_switching', {}).get('observations', 0)}
- **Window Size**: {self.variables.get('markov_switching', {}).get('window_size', 0)}

### 10. Variance Decomposition (Structural VAR)
- **Venues Available**: {self.variables.get('svar', {}).get('venues_available', 0)}
- **Observations**: {self.variables.get('svar', {}).get('observations', 0)}
- **Max Lags**: {self.variables.get('svar', {}).get('max_lags', 0)}
- **Exogenous Variables**: {self.variables.get('svar', {}).get('exogenous_vars', [])}

## Data Files Generated
- `{self.data_dir}/event_study_data.parquet` - Event study data
- `{self.data_dir}/granger_causality_data.parquet` - Granger causality data
- `{self.data_dir}/cointegration_data.parquet` - Cointegration data
- `{self.data_dir}/markov_switching_data.parquet` - Markov switching data
- `{self.data_dir}/svar_data.parquet` - SVAR data

## Status: ✅ READY FOR WAVE-2 TESTING

All variables prepared and ready for econometric deepening tests.
"""
        
        with open(f'{self.output_dir}/wave2_preparation_summary.md', 'w') as f:
            f.write(report)

def main():
    """Main function to prepare Wave-2 variables for both symbols."""
    print("🚀 Wave-2 Variable Preparation")
    print("=" * 50)
    
    symbols = ['BTC-USD', 'ETH-USD']
    
    for symbol in symbols:
        print(f"\n📊 Processing {symbol}...")
        
        # Initialize preparer
        preparer = Wave2VariablePreparer(symbol)
        
        # Prepare variables
        preparer.prepare_all_variables()
        
        # Flag ETH as exploratory
        if symbol == 'ETH-USD':
            print(f"  ⚠️  ETH-USD variables are EXPLORATORY ONLY (insufficient data history)")
    
    print(f"\n🎯 Wave-2 variable preparation complete!")
    print(f"📄 Check analysis/wave2/ directory for output files")

if __name__ == "__main__":
    main()
