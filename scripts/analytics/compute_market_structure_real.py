#!/usr/bin/env python3
"""
Compute Market Structure for Real Panel
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class RealMarketStructureComputer:
    """Compute market structure for real panel."""
    
    def __init__(self):
        self.panel_file = "data/derived/btc_usd/panel_1s_inner_real_single_date.parquet"
        self.output_file = "data/derived/btc_usd/market_structure_real_single_date.parquet"
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
    
    def compute_market_structure(self):
        """Compute market structure for real panel."""
        print("🔧 Computing Market Structure for Real Panel")
        print("=" * 50)
        
        # Load panel
        print("📥 Loading real panel...")
        panel_data = pd.read_parquet(self.panel_file)
        panel_data = panel_data.set_index('ts') if 'ts' in panel_data.columns else panel_data
        
        print(f"📊 Panel: {len(panel_data)} observations")
        print(f"📅 Date range: {panel_data.index.min()} to {panel_data.index.max()}")
        
        # Compute median mid price across venues
        print("📊 Computing median mid price...")
        mid_cols = [f"{venue}_mid_px" for venue in self.venues if f"{venue}_mid_px" in panel_data.columns]
        if not mid_cols:
            print("❌ No mid price columns found")
            return None
        
        panel_data['median_mid'] = panel_data[mid_cols].median(axis=1)
        
        # Create 5-second bars
        print("📊 Creating 5-second bars...")
        bars_5s = self._create_5s_bars(panel_data)
        
        if bars_5s is None or len(bars_5s) == 0:
            print("❌ Failed to create 5-second bars")
            return None
        
        print(f"📊 Created {len(bars_5s)} 5-second bars")
        
        # Compute market structure indicators
        print("🔄 Computing market structure indicators...")
        structure_data = self._compute_structure_indicators(bars_5s)
        
        # Save results
        print("💾 Saving market structure...")
        structure_data.to_parquet(self.output_file)
        
        print(f"✅ Market structure computed")
        print(f"📊 Rows: {len(structure_data)}")
        print(f"📊 Columns: {len(structure_data.columns)}")
        print(f"💾 Saved to {self.output_file}")
        
        return structure_data
    
    def _create_5s_bars(self, panel_data):
        """Create 5-second OHLC bars."""
        try:
            # Resample to 5-second bars
            bars = panel_data['median_mid'].resample('5S').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last'
            })
            
            # Remove bars with insufficient data
            bars = bars.dropna()
            
            return bars
        except Exception as e:
            print(f"❌ Error creating 5-second bars: {e}")
            return None
    
    def _compute_structure_indicators(self, bars):
        """Compute market structure indicators."""
        structure_data = bars.copy()
        
        # Compute ATR14
        print("  📊 Computing ATR14...")
        structure_data['atr14'] = self._compute_atr14(bars)
        
        # Compute fractal swings
        print("  📊 Computing fractal swings...")
        swing_high, swing_low = self._compute_fractal_swings(bars, k=2)
        structure_data['swing_high'] = swing_high
        structure_data['swing_low'] = swing_low
        
        # Compute BOS (Break of Structure)
        print("  📊 Computing BOS...")
        bos_up, bos_dn = self._compute_bos(bars, swing_high, swing_low)
        structure_data['bos_up'] = bos_up
        structure_data['bos_dn'] = bos_dn
        
        # Compute CHoCH (Change of Character)
        print("  📊 Computing CHoCH...")
        choch_up, choch_dn = self._compute_choch(bars, swing_high, swing_low)
        structure_data['choch_up'] = choch_up
        structure_data['choch_dn'] = choch_dn
        
        # Compute structure state
        print("  📊 Computing structure state...")
        structure_data['structure_state'] = self._compute_structure_state(bos_up, bos_dn, choch_up, choch_dn)
        
        return structure_data
    
    def _compute_atr14(self, bars):
        """Compute 14-period ATR."""
        high = bars['high']
        low = bars['low']
        close = bars['close']
        
        # True Range
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR14
        atr14 = true_range.rolling(window=14, min_periods=1).mean()
        
        return atr14
    
    def _compute_fractal_swings(self, bars, k=2):
        """Compute fractal swings."""
        high = bars['high']
        low = bars['low']
        
        swing_high = np.zeros(len(bars))
        swing_low = np.zeros(len(bars))
        
        for i in range(k, len(bars) - k):
            # Swing high: higher than k bars on each side
            if all(high.iloc[i] > high.iloc[i-j] for j in range(1, k+1)) and \
               all(high.iloc[i] > high.iloc[i+j] for j in range(1, k+1)):
                swing_high[i] = 1
            
            # Swing low: lower than k bars on each side
            if all(low.iloc[i] < low.iloc[i-j] for j in range(1, k+1)) and \
               all(low.iloc[i] < low.iloc[i+j] for j in range(1, k+1)):
                swing_low[i] = 1
        
        return swing_high, swing_low
    
    def _compute_bos(self, bars, swing_high, swing_low):
        """Compute Break of Structure (BOS)."""
        bos_up = np.zeros(len(bars))
        bos_dn = np.zeros(len(bars))
        
        last_swing_high = None
        last_swing_low = None
        
        for i in range(len(bars)):
            if swing_high[i] == 1:
                last_swing_high = bars['high'].iloc[i]
            if swing_low[i] == 1:
                last_swing_low = bars['low'].iloc[i]
            
            # BOS Up: price breaks above last swing high
            if last_swing_high is not None and bars['high'].iloc[i] > last_swing_high:
                bos_up[i] = 1
            
            # BOS Down: price breaks below last swing low
            if last_swing_low is not None and bars['low'].iloc[i] < last_swing_low:
                bos_dn[i] = 1
        
        return bos_up, bos_dn
    
    def _compute_choch(self, bars, swing_high, swing_low):
        """Compute Change of Character (CHoCH)."""
        choch_up = np.zeros(len(bars))
        choch_dn = np.zeros(len(bars))
        
        # Simplified CHoCH: when swing direction changes
        for i in range(1, len(bars)):
            if swing_high[i] == 1 and swing_low[i-1] == 1:
                choch_up[i] = 1
            elif swing_low[i] == 1 and swing_high[i-1] == 1:
                choch_dn[i] = 1
        
        return choch_up, choch_dn
    
    def _compute_structure_state(self, bos_up, bos_dn, choch_up, choch_dn):
        """Compute overall structure state."""
        state = np.zeros(len(bos_up), dtype=int)
        
        for i in range(len(bos_up)):
            if bos_up[i] == 1 or choch_up[i] == 1:
                state[i] = 1  # Bullish
            elif bos_dn[i] == 1 or choch_dn[i] == 1:
                state[i] = -1  # Bearish
            else:
                state[i] = 0  # Neutral
        
        return state

if __name__ == "__main__":
    computer = RealMarketStructureComputer()
    computer.compute_market_structure()
