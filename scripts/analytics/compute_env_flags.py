#!/usr/bin/env python3
"""
Compute Environment & Shock Flags for Wave-2 Analysis

Implements environment and shock flags as specified:
- Session labels (UTC timezone)
- Session transitions
- NY open window
- VWAP reset windows
- Per-venue 2-sigma return flags
- Per-venue VWAP deviation flags
- VWAP reset jumps
- Depth regimes (optional)
- Liquidity proxies
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class EnvironmentFlagsComputer:
    """Compute environment and shock flags for econometric analysis."""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.data_dir = f"data/derived/{symbol.replace('-', '_').lower()}"
        self.panel_file = f"{self.data_dir}/panel_1s_inner.parquet"
        self.output_file = f"{self.data_dir}/env_flags_1s.parquet"
        
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        self.panel_data = None
        self.env_flags = None
        
    def compute_all_flags(self):
        """Compute all environment and shock flags."""
        print(f"🔧 Computing Environment Flags for {self.symbol}")
        print("=" * 50)
        
        # Load panel data
        self._load_panel_data()
        
        if self.panel_data is None or self.panel_data.empty:
            print("❌ No panel data found")
            return
        
        print(f"📊 Loaded panel: {len(self.panel_data)} observations")
        
        # Initialize environment flags dataframe
        self.env_flags = pd.DataFrame(index=self.panel_data.index)
        self.env_flags['ts'] = self.panel_data.index
        
        # Compute all flag types
        self._compute_session_flags()
        self._compute_shock_flags()
        self._compute_liquidity_proxies()
        
        # Save environment flags
        self._save_env_flags()
        
        print(f"✅ Environment flags computed")
        print(f"📁 Saved to {self.output_file}")
    
    def _load_panel_data(self):
        """Load aligned panel data."""
        if not os.path.exists(self.panel_file):
            print(f"❌ Panel file not found: {self.panel_file}")
            return
        
        self.panel_data = pd.read_parquet(self.panel_file)
        print(f"📥 Loaded panel from {self.panel_file}")
    
    def _compute_session_flags(self):
        """Compute session-related flags."""
        print("🕐 Computing session flags...")
        
        # Extract hour from UTC timestamp
        hours = self.panel_data.index.hour
        
        # Session labels (UTC)
        # Asia [00-08), Europe [08-13), US [13-20), Pacific [20-24)
        session_labels = pd.Series(index=self.panel_data.index, dtype='object')
        session_labels[(hours >= 0) & (hours < 8)] = 'Asia'
        session_labels[(hours >= 8) & (hours < 13)] = 'Europe'
        session_labels[(hours >= 13) & (hours < 20)] = 'US'
        session_labels[(hours >= 20) & (hours < 24)] = 'Pacific'
        
        self.env_flags['session_label'] = session_labels
        
        # Session transitions (±5 minutes of transition times)
        transition_times = [0, 8, 13, 20]  # UTC hours
        is_transition = pd.Series(False, index=self.panel_data.index)
        
        for hour in transition_times:
            # Check if within ±5 minutes of transition
            transition_start = self.panel_data.index.normalize() + pd.Timedelta(hours=hour) - pd.Timedelta(minutes=5)
            transition_end = self.panel_data.index.normalize() + pd.Timedelta(hours=hour) + pd.Timedelta(minutes=5)
            
            mask = (self.panel_data.index >= transition_start) & (self.panel_data.index <= transition_end)
            is_transition[mask] = True
        
        self.env_flags['is_session_transition'] = is_transition.astype(int)
        
        # NY open window [13:30, 13:45] UTC
        ny_open = ((hours == 13) & (self.panel_data.index.minute >= 30)) | \
                  ((hours == 13) & (self.panel_data.index.minute <= 45))
        self.env_flags['is_ny_open'] = ny_open.astype(int)
        
        # VWAP reset window [00:00, 00:05] UTC
        vwap_reset = (hours == 0) & (self.panel_data.index.minute <= 5)
        self.env_flags['is_vwap_reset_window'] = vwap_reset.astype(int)
        
        print(f"  ✅ Session flags computed")
    
    def _compute_shock_flags(self):
        """Compute shock-related flags."""
        print("⚡ Computing shock flags...")
        
        # Per-venue 2-sigma return flags
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            if mid_col in self.panel_data.columns:
                prices = self.panel_data[mid_col].dropna()
                if len(prices) > 100:
                    # Calculate returns
                    returns = np.log(prices).diff()
                    
                    # Rolling 30-minute standard deviation (1800 seconds)
                    window_size = 1800
                    rolling_std = returns.rolling(window=window_size, min_periods=900).std()
                    
                    # 2-sigma flags
                    is_2sigma = (abs(returns) > 2 * rolling_std).astype(int)
                    self.env_flags[f'is_return_2sigma_{venue}'] = is_2sigma
                    
                    # VWAP deviation flags
                    self._compute_vwap_deviation_flags(venue, prices)
        
        # VWAP reset jump flags (daily at UTC midnight)
        self._compute_vwap_reset_jumps()
        
        print(f"  ✅ Shock flags computed")
    
    def _compute_vwap_deviation_flags(self, venue: str, prices: pd.Series):
        """Compute VWAP deviation flags for a venue."""
        # Calculate daily VWAP (reset at UTC midnight)
        daily_vwap = self._calculate_daily_vwap(venue, prices)
        
        if daily_vwap is not None:
            # Deviation from daily VWAP
            deviation = prices - daily_vwap
            
            # Rolling 30-minute standard deviation of price changes
            price_changes = prices.diff()
            rolling_std = price_changes.rolling(window=1800, min_periods=900).std()
            
            # 2-sigma VWAP deviation flags
            is_vwap_dev_2sigma = (abs(deviation) > 2 * rolling_std).astype(int)
            self.env_flags[f'is_vwap_dev_2sigma_{venue}'] = is_vwap_dev_2sigma
    
    def _calculate_daily_vwap(self, venue: str, prices: pd.Series) -> Optional[pd.Series]:
        """Calculate daily VWAP for a venue."""
        # Try to use trade data if available
        last_px_col = f"{venue}_last_px"
        last_sz_col = f"{venue}_last_sz"
        
        if last_px_col in self.panel_data.columns and last_sz_col in self.panel_data.columns:
            # Use trade-based VWAP
            prices_trade = self.panel_data[last_px_col].dropna()
            sizes = self.panel_data[last_sz_col].dropna()
            
            # Align trade data with price data
            common_idx = prices.index.intersection(prices_trade.index)
            if len(common_idx) > 100:
                prices_aligned = prices_trade.loc[common_idx]
                sizes_aligned = sizes.loc[common_idx]
                
                # Calculate VWAP for each day
                daily_vwap = {}
                for date in prices_aligned.index.date:
                    day_mask = prices_aligned.index.date == date
                    day_prices = prices_aligned[day_mask]
                    day_sizes = sizes_aligned[day_mask]
                    
                    if len(day_prices) > 10 and day_sizes.sum() > 0:
                        vwap = (day_prices * day_sizes).sum() / day_sizes.sum()
                        daily_vwap[date] = vwap
                
                # Forward fill VWAP for each day
                vwap_series = pd.Series(index=prices.index, dtype=float)
                for date, vwap_val in daily_vwap.items():
                    day_mask = prices.index.date == date
                    vwap_series[day_mask] = vwap_val
                
                return vwap_series.fillna(method='ffill')
        
        # Fallback to simple mean of mid prices
        daily_means = prices.groupby(prices.index.date).mean()
        vwap_series = pd.Series(index=prices.index, dtype=float)
        for date, mean_price in daily_means.items():
            day_mask = prices.index.date == date
            vwap_series[day_mask] = mean_price
        
        return vwap_series.fillna(method='ffill')
    
    def _compute_vwap_reset_jumps(self):
        """Compute VWAP reset jump flags."""
        # Find UTC midnight timestamps
        midnight_times = self.panel_data.index[self.panel_data.index.hour == 0]
        
        for t0 in midnight_times:
            # Pre-period: [t0-5m, t0)
            pre_start = t0 - pd.Timedelta(minutes=5)
            pre_end = t0
            pre_data = self.panel_data[(self.panel_data.index >= pre_start) & (self.panel_data.index < pre_end)]
            
            # Post-period: [t0, t0+5m]
            post_start = t0
            post_end = t0 + pd.Timedelta(minutes=5)
            post_data = self.panel_data[(self.panel_data.index >= post_start) & (self.panel_data.index <= post_end)]
            
            if len(pre_data) > 10 and len(post_data) > 10:
                # Calculate median mid prices
                pre_mid = pre_data[[f"{venue}_mid_px" for venue in self.venues if f"{venue}_mid_px" in pre_data.columns]].median(axis=1)
                post_mid = post_data[[f"{venue}_mid_px" for venue in self.venues if f"{venue}_mid_px" in post_data.columns]].median(axis=1)
                
                if len(pre_mid) > 0 and len(post_mid) > 0:
                    pre_median = pre_mid.median()
                    post_median = post_mid.median()
                    
                    # Calculate pre-period volatility
                    pre_returns = pre_mid.pct_change().dropna()
                    pre_std = pre_returns.std()
                    
                    if pre_std > 0:
                        # Check if jump is significant (> 2 sigma)
                        jump_magnitude = abs(post_median - pre_median) / pre_std
                        if jump_magnitude > 2:
                            self.env_flags.loc[t0, 'is_vwap_reset_jump'] = 1
                        else:
                            self.env_flags.loc[t0, 'is_vwap_reset_jump'] = 0
    
    def _compute_liquidity_proxies(self):
        """Compute liquidity proxies for each venue."""
        print("💧 Computing liquidity proxies...")
        
        for venue in self.venues:
            # Spread
            bid_col = f"{venue}_best_bid"
            ask_col = f"{venue}_best_ask"
            if bid_col in self.panel_data.columns and ask_col in self.panel_data.columns:
                spread = self.panel_data[ask_col] - self.panel_data[bid_col]
                self.env_flags[f'spread_{venue}'] = spread
            
            # Top of book depth
            bid_sz_col = f"{venue}_best_bid_size"
            ask_sz_col = f"{venue}_best_ask_size"
            if bid_sz_col in self.panel_data.columns and ask_sz_col in self.panel_data.columns:
                tob_depth = self.panel_data[bid_sz_col] + self.panel_data[ask_sz_col]
                self.env_flags[f'tob_depth_{venue}'] = tob_depth
                
                # Imbalance (guard against divide-by-zero)
                total_size = self.panel_data[bid_sz_col] + self.panel_data[ask_sz_col]
                imbalance = np.where(
                    total_size > 0,
                    (self.panel_data[bid_sz_col] - self.panel_data[ask_sz_col]) / total_size,
                    0
                )
                self.env_flags[f'imbalance_{venue}'] = imbalance
            
            # Amihud illiquidity (1-minute windows)
            self._compute_amihud_illiquidity(venue)
            
            # Depth regime (optional)
            self._compute_depth_regime(venue)
        
        print(f"  ✅ Liquidity proxies computed")
    
    def _compute_amihud_illiquidity(self, venue: str):
        """Compute Amihud illiquidity measure."""
        last_px_col = f"{venue}_last_px"
        last_sz_col = f"{venue}_last_sz"
        
        if last_px_col in self.panel_data.columns and last_sz_col in self.panel_data.columns:
            prices = self.panel_data[last_px_col].dropna()
            sizes = self.panel_data[last_sz_col].dropna()
            
            # Align data
            common_idx = prices.index.intersection(sizes.index)
            if len(common_idx) > 100:
                prices_aligned = prices.loc[common_idx]
                sizes_aligned = sizes.loc[common_idx]
                
                # Calculate returns
                returns = prices_aligned.pct_change().dropna()
                
                # 1-minute windows
                amihud = pd.Series(index=common_idx, dtype=float)
                
                for timestamp in common_idx:
                    # 1-minute window
                    window_start = timestamp - pd.Timedelta(minutes=1)
                    window_end = timestamp
                    
                    window_returns = returns[(returns.index >= window_start) & (returns.index <= window_end)]
                    window_sizes = sizes_aligned[(sizes_aligned.index >= window_start) & (sizes_aligned.index <= window_end)]
                    
                    if len(window_returns) > 0 and window_sizes.sum() > 0:
                        # Volume in USD
                        volume_usd = (prices_aligned.loc[window_sizes.index] * window_sizes).sum()
                        
                        if volume_usd > 0:
                            amihud_val = abs(window_returns).mean() / volume_usd
                            amihud.loc[timestamp] = amihud_val
                
                self.env_flags[f'amihud_1m_{venue}'] = amihud
    
    def _compute_depth_regime(self, venue: str):
        """Compute depth regime (thin/normal/deep)."""
        bid_sz_col = f"{venue}_best_bid_size"
        ask_sz_col = f"{venue}_best_ask_size"
        
        if bid_sz_col in self.panel_data.columns and ask_sz_col in self.panel_data.columns:
            total_depth = self.panel_data[bid_sz_col] + self.panel_data[ask_sz_col]
            
            # Winsorize at 1%
            total_depth_winsor = total_depth.clip(
                total_depth.quantile(0.01),
                total_depth.quantile(0.99)
            )
            
            # Intraday quantiles
            depth_regime = pd.Series(index=total_depth_winsor.index, dtype='object')
            
            for date in total_depth_winsor.index.date:
                day_mask = total_depth_winsor.index.date == date
                day_depth = total_depth_winsor[day_mask]
                
                if len(day_depth) > 10:
                    q33 = day_depth.quantile(0.33)
                    q67 = day_depth.quantile(0.67)
                    
                    depth_regime[day_mask & (day_depth <= q33)] = 'thin'
                    depth_regime[day_mask & (day_depth > q33) & (day_depth <= q67)] = 'normal'
                    depth_regime[day_mask & (day_depth > q67)] = 'deep'
            
            self.env_flags[f'depth_regime_{venue}'] = depth_regime
    
    def _save_env_flags(self):
        """Save environment flags to parquet file."""
        if self.env_flags is not None:
            # Ensure ts column is datetime
            self.env_flags['ts'] = pd.to_datetime(self.env_flags['ts'])
            
            # Save to parquet
            self.env_flags.to_parquet(self.output_file)
            
            print(f"💾 Environment flags saved to {self.output_file}")
            print(f"  Rows: {len(self.env_flags)}")
            print(f"  Columns: {len(self.env_flags.columns)}")

def main():
    """Main function."""
    symbol = 'BTC-USD'
    
    # Initialize computer
    computer = EnvironmentFlagsComputer(symbol)
    
    # Compute all flags
    computer.compute_all_flags()

if __name__ == "__main__":
    main()
