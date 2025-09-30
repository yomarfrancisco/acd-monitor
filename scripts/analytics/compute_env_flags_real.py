#!/usr/bin/env python3
"""
Compute Environment Flags for Real Panel
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class RealEnvironmentFlagsComputer:
    """Compute environment flags for real panel."""
    
    def __init__(self):
        self.panel_file = "data/derived/btc_usd/panel_1s_inner_real_single_date.parquet"
        self.output_file = "data/derived/btc_usd/env_flags_1s_real_single_date.parquet"
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
    
    def compute_flags(self):
        """Compute environment flags for real panel."""
        print("🔧 Computing Environment Flags for Real Panel")
        print("=" * 50)
        
        # Load panel
        print("📥 Loading real panel...")
        panel_data = pd.read_parquet(self.panel_file)
        panel_data = panel_data.set_index('ts') if 'ts' in panel_data.columns else panel_data
        
        print(f"📊 Panel: {len(panel_data)} observations")
        print(f"📅 Date range: {panel_data.index.min()} to {panel_data.index.max()}")
        
        # Initialize environment flags dataframe
        env_flags = pd.DataFrame(index=panel_data.index)
        env_flags.index.name = 'ts'
        
        # Compute session labels
        print("🕐 Computing session labels...")
        env_flags['session_label'] = [self._get_session_label(ts.hour) for ts in env_flags.index]
        
        # Compute session transitions
        print("🔄 Computing session transitions...")
        env_flags['is_session_transition'] = self._compute_session_transitions(env_flags.index)
        
        # Compute NY open window
        print("🏛️ Computing NY open window...")
        env_flags['is_ny_open'] = self._compute_ny_open(env_flags.index)
        
        # Compute VWAP reset window
        print("🔄 Computing VWAP reset window...")
        env_flags['is_vwap_reset_window'] = self._compute_vwap_reset_window(env_flags.index)
        
        # Compute per-venue shock flags
        print("⚡ Computing per-venue shock flags...")
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            if mid_col in panel_data.columns:
                # 2-sigma return flags
                returns = panel_data[mid_col].pct_change()
                rolling_std = returns.rolling(window=1800, min_periods=900).std()
                env_flags[f'is_return_2sigma_{venue}'] = (returns.abs() > 2 * rolling_std).astype(int)
                
                # VWAP deviation flags (simplified)
                vwap = panel_data[mid_col].rolling(window=3600, min_periods=1800).mean()
                vwap_dev = (panel_data[mid_col] - vwap) / vwap
                vwap_std = vwap_dev.rolling(window=1800, min_periods=900).std()
                env_flags[f'is_vwap_dev_2sigma_{venue}'] = (vwap_dev.abs() > 2 * vwap_std).astype(int)
            else:
                env_flags[f'is_return_2sigma_{venue}'] = 0
                env_flags[f'is_vwap_dev_2sigma_{venue}'] = 0
        
        # Compute liquidity proxies
        print("💧 Computing liquidity proxies...")
        for venue in self.venues:
            bid_col = f"{venue}_bid_px"
            ask_col = f"{venue}_ask_px"
            if bid_col in panel_data.columns and ask_col in panel_data.columns:
                # Spread
                env_flags[f'spread_{venue}'] = panel_data[ask_col] - panel_data[bid_col]
                
                # TOB depth
                bid_sz_col = f"{venue}_bid_sz"
                ask_sz_col = f"{venue}_ask_sz"
                if bid_sz_col in panel_data.columns and ask_sz_col in panel_data.columns:
                    env_flags[f'tob_depth_{venue}'] = panel_data[bid_sz_col] + panel_data[ask_sz_col]
                    
                    # Imbalance
                    env_flags[f'imbalance_{venue}'] = (panel_data[bid_sz_col] - panel_data[ask_sz_col]) / (panel_data[bid_sz_col] + panel_data[ask_sz_col])
                else:
                    env_flags[f'tob_depth_{venue}'] = np.nan
                    env_flags[f'imbalance_{venue}'] = np.nan
            else:
                env_flags[f'spread_{venue}'] = np.nan
                env_flags[f'tob_depth_{venue}'] = np.nan
                env_flags[f'imbalance_{venue}'] = np.nan
        
        # Save results
        print("💾 Saving environment flags...")
        env_flags.to_parquet(self.output_file)
        
        print(f"✅ Environment flags computed")
        print(f"📊 Rows: {len(env_flags)}")
        print(f"📊 Columns: {len(env_flags.columns)}")
        print(f"💾 Saved to {self.output_file}")
        
        return env_flags
    
    def _get_session_label(self, hour):
        """Get session label based on UTC hour."""
        if 0 <= hour < 8:
            return 'Asia'
        elif 8 <= hour < 13:
            return 'Europe'
        elif 13 <= hour < 20:
            return 'US'
        else:
            return 'Pacific'
    
    def _compute_session_transitions(self, timestamps):
        """Compute session transition flags."""
        transitions = np.zeros(len(timestamps), dtype=int)
        
        for i, ts in enumerate(timestamps):
            hour = ts.hour
            minute = ts.minute
            
            # Check if within ±5 minutes of transition times
            if (hour == 0 and minute <= 5) or (hour == 7 and minute >= 55):
                transitions[i] = 1  # Asia transition
            elif (hour == 8 and minute <= 5) or (hour == 12 and minute >= 55):
                transitions[i] = 1  # Europe transition
            elif (hour == 13 and minute <= 5) or (hour == 19 and minute >= 55):
                transitions[i] = 1  # US transition
            elif (hour == 20 and minute <= 5) or (hour == 23 and minute >= 55):
                transitions[i] = 1  # Pacific transition
        
        return transitions
    
    def _compute_ny_open(self, timestamps):
        """Compute NY open window flags."""
        ny_open = np.zeros(len(timestamps), dtype=int)
        
        for i, ts in enumerate(timestamps):
            hour = ts.hour
            minute = ts.minute
            
            # NY open window: 13:30-13:45 UTC
            if hour == 13 and 30 <= minute <= 45:
                ny_open[i] = 1
        
        return ny_open
    
    def _compute_vwap_reset_window(self, timestamps):
        """Compute VWAP reset window flags."""
        vwap_reset = np.zeros(len(timestamps), dtype=int)
        
        for i, ts in enumerate(timestamps):
            hour = ts.hour
            minute = ts.minute
            
            # VWAP reset window: 00:00-00:05 UTC
            if hour == 0 and minute <= 5:
                vwap_reset[i] = 1
        
        return vwap_reset

if __name__ == "__main__":
    computer = RealEnvironmentFlagsComputer()
    computer.compute_flags()
