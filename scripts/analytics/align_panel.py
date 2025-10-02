#!/usr/bin/env python3
"""
Multi-Venue Panel Alignment for BTC-USD

Creates clean, aligned panel data across all venues for econometric analysis.
Handles time grid resampling, LOCF filling, and outlier handling.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import boto3
import numpy as np
import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

BUCKET = os.getenv("ACD_S3_BUCKET", "acd-monitor-snapshots")
PREFIX = os.getenv("ACD_S3_PREFIX", "snapshots")

s3 = boto3.client("s3")

class PanelAligner:
    """Align multi-venue panel data for econometric analysis."""
    
    def __init__(self, symbol: str, grid_freq: str = "1S", join_type: str = "inner", winsor_pct: float = 0.5):
        self.symbol = symbol
        self.grid_freq = grid_freq
        self.join_type = join_type
        self.winsor_pct = winsor_pct
        self.output_dir = f"analysis/wave1/{symbol.replace('-', '_').lower()}/alignment"
        self.data_dir = f"data/derived/{symbol.replace('-', '_').lower()}"
        
        # Create output directories
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        self.venue_data = {}
        self.aligned_panel = None
        
    def run_alignment(self):
        """Run complete panel alignment process."""
        print(f"🔄 Panel Alignment for {self.symbol}")
        print("=" * 50)
        
        # Load venue data
        self._load_venue_data()
        
        if not self.venue_data:
            print("❌ No venue data loaded")
            return
        
        # Align to common grid
        self._align_to_grid()
        
        # Handle outliers
        if self.winsor_pct > 0:
            self._handle_outliers()
        
        # Save aligned panel
        self._save_aligned_panel()
        
        # Generate alignment report
        self._generate_alignment_report()
        
        print(f"✅ Panel alignment complete")
        print(f"📁 Results saved to {self.output_dir}")
        print(f"📁 Data saved to {self.data_dir}")
    
    def _load_venue_data(self):
        """Load data for all venues."""
        print("📥 Loading venue data...")
        
        # Get recent windows
        windows = self._get_recent_windows()
        
        for venue in self.venues:
            venue_ticks = []
            
            for window in windows:
                try:
                    # Try both parquet naming conventions
                    parquet_key = f"{window}/ticks/{venue}/part-00000.parquet"
                    try:
                        s3.head_object(Bucket=BUCKET, Key=parquet_key)
                    except:
                        parquet_key = f"{window}/ticks/{venue}/part-0000.parquet"
                    
                    parquet_uri = f"s3://{BUCKET}/{parquet_key}"
                    df = pd.read_parquet(parquet_uri, storage_options={"anon": False})
                    
                    if not df.empty:
                        # Standardize schema
                        df = self._standardize_schema(df, venue)
                        venue_ticks.append(df)
                        
                except Exception as e:
                    print(f"  Warning: Could not load {venue} from {window}: {e}")
                    continue
            
            if venue_ticks:
                combined_df = pd.concat(venue_ticks, ignore_index=True)
                combined_df = combined_df.sort_values('ts_exchange').reset_index(drop=True)
                self.venue_data[venue] = combined_df
                print(f"  {venue}: {len(combined_df)} ticks")
            else:
                print(f"  {venue}: No data")
    
    def _get_recent_windows(self) -> List[str]:
        """Get recent window paths."""
        try:
            response = s3.list_objects_v2(
                Bucket=BUCKET,
                Prefix=f"{PREFIX}/{self.symbol}/"
            )
            
            windows = []
            for obj in response.get("Contents", []):
                if obj["Key"].endswith("OVERLAP.json"):
                    window = obj["Key"].replace("/OVERLAP.json", "")
                    windows.append(window)
            
            # Sort by timestamp (newest first) and limit
            windows.sort(reverse=True)
            return windows[:10]  # Limit to recent windows
            
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
                    df[col] = np.nan
        
        # Ensure timestamp is datetime and timezone-aware
        if 'ts_exchange' in df.columns:
            df['ts_exchange'] = pd.to_datetime(df['ts_exchange'])
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
    
    def _align_to_grid(self):
        """Align all venues to common time grid."""
        print(f"🔄 Aligning to {self.grid_freq} grid...")
        
        # Find common time range
        all_timestamps = []
        for venue, df in self.venue_data.items():
            all_timestamps.extend(df['ts_exchange'].tolist())
        
        if not all_timestamps:
            print("❌ No timestamps found")
            return
        
        # Find overlapping time range
        min_time = min([pd.to_datetime(ts) for ts in all_timestamps if pd.notna(ts)])
        max_time = max([pd.to_datetime(ts) for ts in all_timestamps if pd.notna(ts)])
        
        if min_time >= max_time:
            print("❌ No overlapping time range found")
            return
        
        print(f"  Time range: {min_time} to {max_time}")
        
        # Create common time grid
        time_grid = pd.date_range(start=min_time, end=max_time, freq=self.grid_freq, tz='UTC')
        
        # Align each venue to the grid
        aligned_venues = {}
        
        for venue, df in self.venue_data.items():
            # Filter to common time range
            df_filtered = df[
                (df['ts_exchange'] >= min_time) & 
                (df['ts_exchange'] <= max_time)
            ].copy()
            
            if len(df_filtered) < 10:
                print(f"  Warning: {venue} has insufficient data after filtering")
                continue
            
            # Sort by timestamp
            df_filtered = df_filtered.sort_values('ts_exchange')
            
            # Resample to grid with LOCF
            df_filtered = df_filtered.set_index('ts_exchange')
            
            # Resample with LOCF, max fill gap of 3 seconds
            resampled = df_filtered.resample(self.grid_freq).last()
            
            # Check for gaps > 3 seconds and fill with NaN
            time_diff = resampled.index.to_series().diff()
            gap_mask = time_diff > pd.Timedelta('3S')
            resampled.loc[gap_mask, ['mid_px', 'spread', 'best_bid', 'best_ask']] = np.nan
            
            aligned_venues[venue] = resampled
            print(f"  {venue}: {len(resampled)} aligned observations")
        
        # Join venues
        if self.join_type == "inner":
            # Inner join - only common timestamps
            self.aligned_panel = self._inner_join_venues(aligned_venues, time_grid)
        else:
            # Outer join - all timestamps
            self.aligned_panel = self._outer_join_venues(aligned_venues, time_grid)
        
        print(f"  Final panel: {len(self.aligned_panel)} observations")
    
    def _inner_join_venues(self, aligned_venues: Dict, time_grid: pd.DatetimeIndex) -> pd.DataFrame:
        """Create inner join panel."""
        # Find common timestamps across all venues
        common_timestamps = None
        
        for venue, df in aligned_venues.items():
            venue_timestamps = df.index[df['mid_px'].notna()]
            if common_timestamps is None:
                common_timestamps = venue_timestamps
            else:
                common_timestamps = common_timestamps.intersection(venue_timestamps)
        
        if len(common_timestamps) == 0:
            print("❌ No common timestamps found for inner join")
            return pd.DataFrame()
        
        # Create panel with common timestamps
        panel_data = {}
        
        for venue, df in aligned_venues.items():
            venue_common = df.loc[common_timestamps]
            panel_data[f"{venue}_mid_px"] = venue_common['mid_px']
            panel_data[f"{venue}_spread"] = venue_common['spread']
            panel_data[f"{venue}_best_bid"] = venue_common['best_bid']
            panel_data[f"{venue}_best_ask"] = venue_common['best_ask']
        
        panel_df = pd.DataFrame(panel_data, index=common_timestamps)
        return panel_df
    
    def _outer_join_venues(self, aligned_venues: Dict, time_grid: pd.DatetimeIndex) -> pd.DataFrame:
        """Create outer join panel."""
        panel_data = {}
        
        for venue, df in aligned_venues.items():
            # Reindex to full time grid
            df_reindexed = df.reindex(time_grid)
            panel_data[f"{venue}_mid_px"] = df_reindexed['mid_px']
            panel_data[f"{venue}_spread"] = df_reindexed['spread']
            panel_data[f"{venue}_best_bid"] = df_reindexed['best_bid']
            panel_data[f"{venue}_best_ask"] = df_reindexed['best_ask']
        
        panel_df = pd.DataFrame(panel_data, index=time_grid)
        return panel_df
    
    def _handle_outliers(self):
        """Handle outliers using winsorization."""
        print(f"🔧 Handling outliers (winsorize {self.winsor_pct}%)...")
        
        if self.aligned_panel is None or self.aligned_panel.empty:
            return
        
        # Winsorize returns for each venue
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            if mid_col in self.aligned_panel.columns:
                # Calculate returns
                returns = self.aligned_panel[mid_col].pct_change()
                
                # Winsorize returns
                lower_bound = returns.quantile(self.winsor_pct / 100)
                upper_bound = returns.quantile(1 - self.winsor_pct / 100)
                
                returns_winsorized = returns.clip(lower_bound, upper_bound)
                
                # Reconstruct prices from winsorized returns
                prices_original = self.aligned_panel[mid_col].iloc[0]
                prices_winsorized = [prices_original]
                
                for ret in returns_winsorized.iloc[1:]:
                    if pd.notna(ret):
                        prices_winsorized.append(prices_winsorized[-1] * (1 + ret))
                    else:
                        prices_winsorized.append(np.nan)
                
                self.aligned_panel[mid_col] = prices_winsorized
        
        print(f"  ✅ Outlier handling complete")
    
    def _save_aligned_panel(self):
        """Save aligned panel to parquet files."""
        if self.aligned_panel is None or self.aligned_panel.empty:
            print("❌ No aligned panel to save")
            return
        
        # Save inner join panel
        inner_file = f"{self.data_dir}/panel_{self.grid_freq}_inner.parquet"
        self.aligned_panel.to_parquet(inner_file)
        print(f"  💾 Saved inner panel: {inner_file}")
        
        # For outer join, create a separate file
        if self.join_type == "outer":
            outer_file = f"{self.data_dir}/panel_{self.grid_freq}_outer.parquet"
            self.aligned_panel.to_parquet(outer_file)
            print(f"  💾 Saved outer panel: {outer_file}")
    
    def _generate_alignment_report(self):
        """Generate alignment report."""
        if self.aligned_panel is None or self.aligned_panel.empty:
            return
        
        # Calculate alignment statistics
        total_obs = len(self.aligned_panel)
        venue_stats = {}
        
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            if mid_col in self.aligned_panel.columns:
                non_null_count = self.aligned_panel[mid_col].notna().sum()
                venue_stats[venue] = {
                    'observations': non_null_count,
                    'coverage': non_null_count / total_obs,
                    'mean_price': self.aligned_panel[mid_col].mean(),
                    'std_price': self.aligned_panel[mid_col].std()
                }
        
        # Generate report
        report = f"""# Panel Alignment Report - {self.symbol}

## Alignment Parameters
- **Grid Frequency**: {self.grid_freq}
- **Join Type**: {self.join_type}
- **Winsorization**: {self.winsor_pct}%
- **Total Observations**: {total_obs:,}

## Venue Coverage
"""
        
        for venue, stats in venue_stats.items():
            report += f"- **{venue}**: {stats['observations']:,} obs ({stats['coverage']:.1%} coverage)\n"
        
        report += f"""
## Data Quality
- **Time Range**: {self.aligned_panel.index.min()} to {self.aligned_panel.index.max()}
- **Duration**: {(self.aligned_panel.index.max() - self.aligned_panel.index.min()).total_seconds() / 3600:.1f} hours

## Files Generated
- `{self.data_dir}/panel_{self.grid_freq}_inner.parquet`
- `{self.data_dir}/panel_{self.grid_freq}_outer.parquet` (if outer join)

## Next Steps
- Use aligned panel for cross-correlation analysis
- Enable PCA factor analysis
- Re-run variance ratio tests on aligned data
"""
        
        with open(f'{self.output_dir}/panel_build_report.md', 'w') as f:
            f.write(report)
        
        # Save summary statistics
        summary_data = {
            'alignment_params': {
                'grid_freq': self.grid_freq,
                'join_type': self.join_type,
                'winsor_pct': self.winsor_pct
            },
            'panel_stats': {
                'total_observations': total_obs,
                'time_range_hours': (self.aligned_panel.index.max() - self.aligned_panel.index.min()).total_seconds() / 3600
            },
            'venue_coverage': venue_stats
        }
        
        with open(f'{self.output_dir}/alignment_summary.json', 'w') as f:
            json.dump(summary_data, f, indent=2, default=str)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Multi-Venue Panel Alignment')
    parser.add_argument('--symbol', default='BTC-USD', help='Symbol to align')
    parser.add_argument('--grid', default='1S', help='Grid frequency (1S, 250ms)')
    parser.add_argument('--join', default='inner', choices=['inner', 'outer'], help='Join type')
    parser.add_argument('--winsor', type=float, default=0.5, help='Winsorization percentage')
    
    args = parser.parse_args()
    
    # Initialize aligner
    aligner = PanelAligner(args.symbol, args.grid, args.join, args.winsor)
    
    # Run alignment
    aligner.run_alignment()

if __name__ == "__main__":
    main()
