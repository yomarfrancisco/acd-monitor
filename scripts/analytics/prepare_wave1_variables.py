#!/usr/bin/env python3
"""
Prepare variables for Wave-1 econometric tests (Baseline Statistical Screens)

Tests 1-5:
1. Variance Ratio Test
2. Autocorrelation & AR(1) Decay  
3. Cross-Correlation of Prices/Spreads
4. PCA Loadings / Common Factor Analysis
5. Rolling Volatility & Spread Convergence
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import boto3
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

BUCKET = os.getenv("ACD_S3_BUCKET", "acd-monitor-snapshots")
PREFIX = os.getenv("ACD_S3_PREFIX", "snapshots")
SYMBOLS = ["BTC-USD", "ETH-USD"]
VENUES = ["binance", "coinbase", "kraken", "okx", "bybit"]

s3 = boto3.client("s3")

class Wave1VariablePreparer:
    """Prepare variables for Wave-1 econometric tests."""
    
    def __init__(self, symbol: str, venues: List[str]):
        self.symbol = symbol
        self.venues = venues
        self.data = {}
        self.variables = {}
        
    def load_recent_data(self, days_back: int = 7) -> Dict:
        """Load recent tick data from S3."""
        print(f"📊 Loading recent data for {self.symbol}...")
        
        # Get recent windows
        windows = self._get_recent_windows(days_back)
        print(f"  Found {len(windows)} windows")
        
        venue_data = {}
        for venue in self.venues:
            venue_data[venue] = []
            
        # Load data from each window
        for window in windows:
            for venue in self.venues:
                try:
                    # Load parquet data (try both naming conventions)
                    parquet_key = f"{window}/ticks/{venue}/part-00000.parquet"
                    try:
                        # Check if file exists
                        s3.head_object(Bucket=BUCKET, Key=parquet_key)
                    except:
                        # Try alternative naming
                        parquet_key = f"{window}/ticks/{venue}/part-0000.parquet"
                    parquet_uri = f"s3://{BUCKET}/{parquet_key}"
                    
                    df = pd.read_parquet(parquet_uri, storage_options={"anon": False})
                    
                    if not df.empty:
                        # Ensure canonical schema
                        df = self._standardize_schema(df, venue)
                        venue_data[venue].append(df)
                        
                except Exception as e:
                    print(f"    Warning: Could not load {venue} from {window}: {e}")
                    continue
        
        # Combine data for each venue
        for venue in self.venues:
            if venue_data[venue]:
                combined_df = pd.concat(venue_data[venue], ignore_index=True)
                combined_df = combined_df.sort_values('ts_exchange').reset_index(drop=True)
                self.data[venue] = combined_df
                print(f"  {venue}: {len(combined_df)} ticks")
            else:
                print(f"  {venue}: No data")
                self.data[venue] = pd.DataFrame()
        
        return self.data
    
    def _get_recent_windows(self, days_back: int) -> List[str]:
        """Get recent window paths from S3."""
        try:
            response = s3.list_objects_v2(
                Bucket=BUCKET,
                Prefix=f"{PREFIX}/{self.symbol}/"
            )
            
            windows = []
            for obj in response.get("Contents", []):
                if obj["Key"].endswith("OVERLAP.json"):
                    # Extract window path
                    window = obj["Key"].replace("/OVERLAP.json", "")
                    windows.append(window)
            
            # Sort by timestamp (newest first)
            windows.sort(reverse=True)
            return windows[:days_back * 2]  # Assume 2 windows per day
            
        except Exception as e:
            print(f"Error getting windows: {e}")
            return []
    
    def _standardize_schema(self, df: pd.DataFrame, venue: str) -> pd.DataFrame:
        """Ensure canonical schema alignment."""
        # Ensure required columns exist
        required_cols = ['ts_exchange', 'best_bid', 'best_ask', 'last_px']
        
        for col in required_cols:
            if col not in df.columns:
                if col == 'ts_exchange' and 'timestamp' in df.columns:
                    df[col] = df['timestamp']
                elif col in ['best_bid', 'best_ask'] and 'price' in df.columns:
                    df[col] = df['price']
                elif col == 'last_px' and 'price' in df.columns:
                    df[col] = df['price']
                else:
                    # Fill with NaN if column doesn't exist
                    df[col] = np.nan
        
        # Ensure timestamp is datetime and timezone-aware
        if 'ts_exchange' in df.columns:
            df['ts_exchange'] = pd.to_datetime(df['ts_exchange'])
            # Ensure all timestamps are timezone-aware (UTC)
            if df['ts_exchange'].dt.tz is None:
                df['ts_exchange'] = df['ts_exchange'].dt.tz_localize('UTC')
            else:
                df['ts_exchange'] = df['ts_exchange'].dt.tz_convert('UTC')
        
        # Calculate mid price and spread
        if 'best_bid' in df.columns and 'best_ask' in df.columns:
            df['mid_px'] = (df['best_bid'] + df['best_ask']) / 2
            df['spread'] = df['best_ask'] - df['best_bid']
            df['spread_bps'] = (df['spread'] / df['mid_px']) * 10000
        
        # Add venue identifier
        df['venue'] = venue
        
        return df
    
    def prepare_wave1_variables(self) -> Dict:
        """Prepare all variables for Wave-1 tests."""
        print(f"🔧 Preparing Wave-1 variables for {self.symbol}...")
        
        # Test 1: Variance Ratio Test
        self._prepare_variance_ratio_variables()
        
        # Test 2: Autocorrelation & AR(1) Decay
        self._prepare_autocorrelation_variables()
        
        # Test 3: Cross-Correlation of Prices/Spreads
        self._prepare_cross_correlation_variables()
        
        # Test 4: PCA Loadings / Common Factor Analysis
        self._prepare_pca_variables()
        
        # Test 5: Rolling Volatility & Spread Convergence
        self._prepare_volatility_variables()
        
        return self.variables
    
    def _prepare_variance_ratio_variables(self):
        """Test 1: Variance Ratio Test variables."""
        print("  📈 Preparing variance ratio variables...")
        
        variance_ratios = {}
        
        for venue in self.venues:
            if venue not in self.data or self.data[venue].empty:
                continue
                
            df = self.data[venue].copy()
            if 'mid_px' not in df.columns:
                continue
            
            # Calculate returns
            df = df.sort_values('ts_exchange')
            df['returns'] = df['mid_px'].pct_change()
            df = df.dropna()
            
            if len(df) < 100:  # Need sufficient data
                continue
            
            # Variance ratio for different lags
            lags = [2, 4, 8, 16, 32]
            vr_results = {}
            
            for lag in lags:
                if len(df) < lag * 10:  # Need sufficient data
                    continue
                    
                # Calculate variance ratio
                returns = df['returns'].values
                n = len(returns)
                
                # Var(rt + rt-1 + ... + rt-k+1) / k*Var(rt)
                k_returns = []
                for i in range(lag, n):
                    k_returns.append(returns[i-lag+1:i+1].sum())
                
                if len(k_returns) > 10:
                    var_k = np.var(k_returns)
                    var_1 = np.var(returns[lag:])
                    vr = var_k / (lag * var_1) if var_1 > 0 else np.nan
                    vr_results[f'vr_{lag}'] = vr
            
            variance_ratios[venue] = vr_results
        
        self.variables['variance_ratios'] = variance_ratios
    
    def _prepare_autocorrelation_variables(self):
        """Test 2: Autocorrelation & AR(1) Decay variables."""
        print("  🔄 Preparing autocorrelation variables...")
        
        autocorrelations = {}
        
        for venue in self.venues:
            if venue not in self.data or self.data[venue].empty:
                continue
                
            df = self.data[venue].copy()
            if 'mid_px' not in df.columns:
                continue
            
            # Calculate returns
            df = df.sort_values('ts_exchange')
            df['returns'] = df['mid_px'].pct_change()
            df = df.dropna()
            
            if len(df) < 50:
                continue
            
            returns = df['returns'].values
            
            # Calculate autocorrelations for different lags
            lags = [1, 2, 3, 5, 10, 20]
            ac_results = {}
            
            for lag in lags:
                if len(returns) > lag:
                    ac = np.corrcoef(returns[:-lag], returns[lag:])[0, 1]
                    ac_results[f'ac_lag_{lag}'] = ac
            
            # AR(1) coefficient
            if len(returns) > 1:
                try:
                    from statsmodels.tsa.ar_model import AutoReg
                    model = AutoReg(returns, lags=1)
                    fitted = model.fit()
                    ac_results['ar1_coef'] = fitted.params[1] if len(fitted.params) > 1 else np.nan
                except:
                    ac_results['ar1_coef'] = np.nan
            
            autocorrelations[venue] = ac_results
        
        self.variables['autocorrelations'] = autocorrelations
    
    def _prepare_cross_correlation_variables(self):
        """Test 3: Cross-Correlation of Prices/Spreads variables."""
        print("  🔗 Preparing cross-correlation variables...")
        
        # Get aligned time series for all venues
        aligned_data = self._align_venue_data()
        
        if len(aligned_data) < 2:
            print("    Warning: Need at least 2 venues for cross-correlation")
            return
        
        cross_correlations = {}
        
        # Price cross-correlations
        price_corrs = {}
        for i, venue1 in enumerate(aligned_data.keys()):
            for j, venue2 in enumerate(aligned_data.keys()):
                if i < j:  # Avoid duplicates
                    df1 = aligned_data[venue1]
                    df2 = aligned_data[venue2]
                    
                    if 'mid_px' in df1.columns and 'mid_px' in df2.columns:
                        # Calculate returns
                        ret1 = df1['mid_px'].pct_change().dropna()
                        ret2 = df2['mid_px'].pct_change().dropna()
                        
                        # Align series
                        common_idx = ret1.index.intersection(ret2.index)
                        if len(common_idx) > 10:
                            ret1_aligned = ret1.loc[common_idx]
                            ret2_aligned = ret2.loc[common_idx]
                            
                            corr = np.corrcoef(ret1_aligned, ret2_aligned)[0, 1]
                            price_corrs[f'{venue1}_{venue2}'] = corr
        
        cross_correlations['price_correlations'] = price_corrs
        
        # Spread cross-correlations
        spread_corrs = {}
        for i, venue1 in enumerate(aligned_data.keys()):
            for j, venue2 in enumerate(aligned_data.keys()):
                if i < j:
                    df1 = aligned_data[venue1]
                    df2 = aligned_data[venue2]
                    
                    if 'spread' in df1.columns and 'spread' in df2.columns:
                        spread1 = df1['spread'].dropna()
                        spread2 = df2['spread'].dropna()
                        
                        common_idx = spread1.index.intersection(spread2.index)
                        if len(common_idx) > 10:
                            spread1_aligned = spread1.loc[common_idx]
                            spread2_aligned = spread2.loc[common_idx]
                            
                            corr = np.corrcoef(spread1_aligned, spread2_aligned)[0, 1]
                            spread_corrs[f'{venue1}_{venue2}'] = corr
        
        cross_correlations['spread_correlations'] = spread_corrs
        
        self.variables['cross_correlations'] = cross_correlations
    
    def _prepare_pca_variables(self):
        """Test 4: PCA Loadings / Common Factor Analysis variables."""
        print("  🎯 Preparing PCA variables...")
        
        # Get aligned data
        aligned_data = self._align_venue_data()
        
        if len(aligned_data) < 3:
            print("    Warning: Need at least 3 venues for PCA")
            return
        
        # Prepare standardized returns matrix
        venue_returns = {}
        for venue, df in aligned_data.items():
            if 'mid_px' in df.columns:
                returns = df['mid_px'].pct_change().dropna()
                venue_returns[venue] = returns
        
        if len(venue_returns) < 3:
            print("    Warning: Need at least 3 venues with returns for PCA")
            return
        
        # Align all series to common time index
        common_idx = None
        for venue, returns in venue_returns.items():
            if common_idx is None:
                common_idx = returns.index
            else:
                common_idx = common_idx.intersection(returns.index)
        
        if len(common_idx) < 50:
            print("    Warning: Need at least 50 common observations for PCA")
            return
        
        # Create aligned returns matrix
        aligned_returns = {}
        for venue, returns in venue_returns.items():
            aligned_returns[venue] = returns.loc[common_idx]
        
        # Convert to DataFrame and standardize
        returns_df = pd.DataFrame(aligned_returns)
        returns_df = returns_df.dropna()
        
        if len(returns_df) < 50:
            print("    Warning: Insufficient data after alignment")
            return
        
        # Standardize returns
        scaler = StandardScaler()
        returns_std = scaler.fit_transform(returns_df)
        
        # Perform PCA
        pca = PCA()
        pca_result = pca.fit_transform(returns_std)
        
        # Extract results
        pca_vars = {
            'explained_variance_ratio': pca.explained_variance_ratio_.tolist(),
            'cumulative_variance_ratio': np.cumsum(pca.explained_variance_ratio_).tolist(),
            'components': pca.components_.tolist(),
            'n_components': pca.n_components_,
            'venues': list(returns_df.columns)
        }
        
        # First component loadings (coordination factor)
        if len(pca.components_) > 0:
            first_component = pca.components_[0]
            pca_vars['first_component_loadings'] = {
                venue: loading for venue, loading in zip(returns_df.columns, first_component)
            }
        
        self.variables['pca_analysis'] = pca_vars
    
    def _prepare_volatility_variables(self):
        """Test 5: Rolling Volatility & Spread Convergence variables."""
        print("  📊 Preparing volatility variables...")
        
        volatility_data = {}
        
        for venue in self.venues:
            if venue not in self.data or self.data[venue].empty:
                continue
                
            df = self.data[venue].copy()
            if 'mid_px' not in df.columns:
                continue
            
            # Calculate returns
            df = df.sort_values('ts_exchange')
            df['returns'] = df['mid_px'].pct_change()
            df = df.dropna()
            
            if len(df) < 100:
                continue
            
            # Rolling volatility (30-minute windows)
            window_size = min(30, len(df) // 4)  # Adaptive window size
            df['rolling_vol'] = df['returns'].rolling(window=window_size).std()
            
            # Rolling spread statistics
            if 'spread' in df.columns:
                df['rolling_spread_mean'] = df['spread'].rolling(window=window_size).mean()
                df['rolling_spread_std'] = df['spread'].rolling(window=window_size).std()
            
            # Calculate convergence metrics
            vol_stats = {
                'mean_volatility': df['rolling_vol'].mean(),
                'volatility_std': df['rolling_vol'].std(),
                'volatility_range': df['rolling_vol'].max() - df['rolling_vol'].min()
            }
            
            if 'spread' in df.columns:
                vol_stats.update({
                    'mean_spread': df['rolling_spread_mean'].mean(),
                    'spread_std': df['rolling_spread_std'].mean(),
                    'spread_convergence': df['rolling_spread_std'].mean() / df['rolling_spread_mean'].mean() if df['rolling_spread_mean'].mean() > 0 else np.nan
                })
            
            volatility_data[venue] = vol_stats
        
        self.variables['volatility_analysis'] = volatility_data
    
    def _align_venue_data(self) -> Dict[str, pd.DataFrame]:
        """Align data across venues by timestamp."""
        if len(self.data) < 2:
            return {}
        
        # Find common time range
        all_timestamps = []
        for venue, df in self.data.items():
            if not df.empty and 'ts_exchange' in df.columns:
                all_timestamps.extend(df['ts_exchange'].tolist())
        
        if not all_timestamps:
            return {}
        
        # Find overlapping time range
        min_time = max([pd.to_datetime(ts) for ts in all_timestamps if pd.notna(ts)])
        max_time = min([pd.to_datetime(ts) for ts in all_timestamps if pd.notna(ts)])
        
        if min_time >= max_time:
            return {}
        
        # Filter data to common time range
        aligned_data = {}
        for venue, df in self.data.items():
            if not df.empty and 'ts_exchange' in df.columns:
                df_filtered = df[
                    (df['ts_exchange'] >= min_time) & 
                    (df['ts_exchange'] <= max_time)
                ].copy()
                
                if len(df_filtered) > 10:  # Need sufficient data
                    aligned_data[venue] = df_filtered
        
        return aligned_data
    
    def save_variables(self, output_path: str):
        """Save prepared variables to file."""
        output_data = {
            'symbol': self.symbol,
            'timestamp': datetime.utcnow().isoformat(),
            'venues_analyzed': list(self.data.keys()),
            'variables': self.variables
        }
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        
        print(f"💾 Variables saved to {output_path}")

def main():
    """Main function to prepare Wave-1 variables for all symbols."""
    print("🚀 Wave-1 Variable Preparation")
    print("=" * 50)
    
    for symbol in SYMBOLS:
        print(f"\n📊 Processing {symbol}...")
        
        # Initialize preparer
        preparer = Wave1VariablePreparer(symbol, VENUES)
        
        # Load recent data
        data = preparer.load_recent_data(days_back=7)
        
        if not data:
            print(f"  ❌ No data found for {symbol}")
            continue
        
        # Prepare variables
        variables = preparer.prepare_wave1_variables()
        
        # Save variables
        output_path = f"reports/wave1_variables_{symbol.replace('-', '_').lower()}.json"
        preparer.save_variables(output_path)
        
        # Print summary
        print(f"  ✅ Variables prepared for {symbol}")
        print(f"    Venues: {len([v for v in data.values() if not v.empty])}")
        print(f"    Tests: {len(variables)}")
    
    print(f"\n🎯 Wave-1 variable preparation complete!")
    print(f"📄 Check reports/ directory for output files")

if __name__ == "__main__":
    main()
