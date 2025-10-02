#!/usr/bin/env python3
"""
Compute Market Structure (CHoCH/BOS) for Wave-2 Analysis

Implements fractal CHoCH/BOS analysis:
- Build 5s bars from median mid across venues
- Compute fractal swings (k=2)
- Calculate ATR14 for robust buffers
- Implement BOS (MSB) and CHoCH (MSS) logic
- Track structure state transitions
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class MarketStructureComputer:
    """Compute market structure using CHoCH/BOS methodology."""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.data_dir = f"data/derived/{symbol.replace('-', '_').lower()}"
        self.panel_file = f"{self.data_dir}/panel_1s_inner.parquet"
        self.output_file = f"{self.data_dir}/market_structure.parquet"
        
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        self.panel_data = None
        self.bars_5s = None
        self.structure_data = None
        
    def compute_market_structure(self):
        """Compute market structure using CHoCH/BOS."""
        print(f"🏗️ Computing Market Structure for {self.symbol}")
        print("=" * 50)
        
        # Load panel data
        self._load_panel_data()
        
        if self.panel_data is None or self.panel_data.empty:
            print("❌ No panel data found")
            return
        
        print(f"📊 Loaded panel: {len(self.panel_data)} observations")
        
        # Build 5-second bars
        self._build_5s_bars()
        
        if self.bars_5s is None or self.bars_5s.empty:
            print("❌ No bars created")
            return
        
        print(f"📊 Created {len(self.bars_5s)} 5-second bars")
        
        # Compute market structure
        self._compute_fractal_swings()
        self._compute_atr14()
        self._compute_bos_choch()
        
        # Save market structure
        self._save_market_structure()
        
        print(f"✅ Market structure computed")
        print(f"📁 Saved to {self.output_file}")
    
    def _load_panel_data(self):
        """Load aligned panel data."""
        if not os.path.exists(self.panel_file):
            print(f"❌ Panel file not found: {self.panel_file}")
            return
        
        self.panel_data = pd.read_parquet(self.panel_file)
        print(f"📥 Loaded panel from {self.panel_file}")
    
    def _build_5s_bars(self):
        """Build 5-second OHLC bars from median mid across venues."""
        print("📊 Building 5-second bars...")
        
        # Get median mid price across all venues
        mid_columns = [f"{venue}_mid_px" for venue in self.venues if f"{venue}_mid_px" in self.panel_data.columns]
        
        if len(mid_columns) < 2:
            print("❌ Insufficient venue data for median calculation")
            return
        
        # Calculate median mid price
        mid_prices = self.panel_data[mid_columns].median(axis=1)
        mid_prices = mid_prices.dropna()
        
        if len(mid_prices) < 100:
            print("❌ Insufficient price data")
            return
        
        # Resample to 5-second bars
        bars = mid_prices.resample('5S').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        })
        
        # Remove bars with insufficient data
        bars = bars.dropna()
        
        if len(bars) < 20:
            print("❌ Insufficient bars created")
            return
        
        self.bars_5s = bars
        print(f"  ✅ Created {len(bars)} 5-second bars")
    
    def _compute_fractal_swings(self):
        """Compute fractal swings with k=2."""
        print("🔄 Computing fractal swings...")
        
        # Initialize swing columns
        self.bars_5s['swing_high'] = 0
        self.bars_5s['swing_low'] = 0
        
        k = 2  # Fractal window
        
        # Find swing highs
        for i in range(k, len(self.bars_5s) - k):
            if (self.bars_5s['high'].iloc[i] > self.bars_5s['high'].iloc[i-k:i].max() and
                self.bars_5s['high'].iloc[i] > self.bars_5s['high'].iloc[i+1:i+k+1].max()):
                self.bars_5s.iloc[i, self.bars_5s.columns.get_loc('swing_high')] = 1
        
        # Find swing lows
        for i in range(k, len(self.bars_5s) - k):
            if (self.bars_5s['low'].iloc[i] < self.bars_5s['low'].iloc[i-k:i].min() and
                self.bars_5s['low'].iloc[i] < self.bars_5s['low'].iloc[i+1:i+k+1].min()):
                self.bars_5s.iloc[i, self.bars_5s.columns.get_loc('swing_low')] = 1
        
        print(f"  ✅ Fractal swings computed")
    
    def _compute_atr14(self):
        """Compute ATR14 for robust buffers."""
        print("📏 Computing ATR14...")
        
        # Calculate True Range
        high_low = self.bars_5s['high'] - self.bars_5s['low']
        high_close_prev = abs(self.bars_5s['high'] - self.bars_5s['close'].shift(1))
        low_close_prev = abs(self.bars_5s['low'] - self.bars_5s['close'].shift(1))
        
        true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        
        # Calculate ATR14 (14-period average of True Range)
        self.bars_5s['atr14'] = true_range.rolling(window=14, min_periods=1).mean()
        
        print(f"  ✅ ATR14 computed")
    
    def _compute_bos_choch(self):
        """Compute BOS (MSB) and CHoCH (MSS) logic."""
        print("🎯 Computing BOS/CHoCH...")
        
        # Initialize columns
        self.bars_5s['bos_up'] = 0
        self.bars_5s['bos_dn'] = 0
        self.bars_5s['choch_up'] = 0
        self.bars_5s['choch_dn'] = 0
        self.bars_5s['structure_state'] = 'neutral'
        self.bars_5s['last_swing_high'] = np.nan
        self.bars_5s['last_swing_low'] = np.nan
        
        # Initialize tracking variables
        last_swing_high = None
        last_swing_low = None
        structure_state = 'neutral'
        
        # Process each bar
        for i in range(len(self.bars_5s)):
            current_bar = self.bars_5s.iloc[i]
            
            # Update last swing levels
            if current_bar['swing_high'] == 1:
                last_swing_high = current_bar['high']
                self.bars_5s.iloc[i, self.bars_5s.columns.get_loc('last_swing_high')] = last_swing_high
            
            if current_bar['swing_low'] == 1:
                last_swing_low = current_bar['low']
                self.bars_5s.iloc[i, self.bars_5s.columns.get_loc('last_swing_low')] = last_swing_low
            
            # Check for BOS (Break of Structure)
            if last_swing_high is not None and current_bar['close'] > last_swing_high + 0.25 * current_bar['atr14']:
                self.bars_5s.iloc[i, self.bars_5s.columns.get_loc('bos_up')] = 1
                
                # Check for CHoCH (Change of Character)
                if structure_state == 'down':
                    self.bars_5s.iloc[i, self.bars_5s.columns.get_loc('choch_up')] = 1
                    structure_state = 'up'
            
            if last_swing_low is not None and current_bar['close'] < last_swing_low - 0.25 * current_bar['atr14']:
                self.bars_5s.iloc[i, self.bars_5s.columns.get_loc('bos_dn')] = 1
                
                # Check for CHoCH (Change of Character)
                if structure_state == 'up':
                    self.bars_5s.iloc[i, self.bars_5s.columns.get_loc('choch_dn')] = 1
                    structure_state = 'down'
            
            # Update structure state
            self.bars_5s.iloc[i, self.bars_5s.columns.get_loc('structure_state')] = structure_state
        
        print(f"  ✅ BOS/CHoCH computed")
    
    def _save_market_structure(self):
        """Save market structure to parquet file."""
        if self.bars_5s is not None:
            # Add bar metadata
            self.bars_5s['bar_ts'] = self.bars_5s.index
            self.bars_5s['bar_size'] = '5s'
            
            # Reorder columns
            columns = ['bar_ts', 'bar_size', 'open', 'high', 'low', 'close', 'atr14',
                      'swing_high', 'swing_low', 'last_swing_high', 'last_swing_low',
                      'bos_up', 'bos_dn', 'choch_up', 'choch_dn', 'structure_state']
            
            # Only include columns that exist
            available_columns = [col for col in columns if col in self.bars_5s.columns]
            self.structure_data = self.bars_5s[available_columns].copy()
            
            # Save to parquet
            self.structure_data.to_parquet(self.output_file)
            
            print(f"💾 Market structure saved to {self.output_file}")
            print(f"  Rows: {len(self.structure_data)}")
            print(f"  Columns: {len(self.structure_data.columns)}")

def main():
    """Main function."""
    symbol = 'BTC-USD'
    
    # Initialize computer
    computer = MarketStructureComputer(symbol)
    
    # Compute market structure
    computer.compute_market_structure()

if __name__ == "__main__":
    main()
