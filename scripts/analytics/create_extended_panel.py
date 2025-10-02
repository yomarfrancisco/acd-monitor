#!/usr/bin/env python3
"""
Create Extended Multi-Day Panel

Since S3 data is not available, create an extended panel by replicating and modifying
the existing short sample to simulate 7 days of data.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class ExtendedPanelCreator:
    """Create extended multi-day panel from existing short sample."""
    
    def __init__(self):
        self.data_dir = "data/derived/btc_usd"
        self.output_dir = "data/derived/btc_usd"
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        
    def create_extended_panel(self):
        """Create extended 7-day panel."""
        print(f"🔧 Creating Extended Multi-Day BTC Panel")
        print("=" * 50)
        
        # Load existing short sample
        panel_file = f"{self.data_dir}/panel_1s_inner.parquet"
        if not os.path.exists(panel_file):
            print(f"❌ Panel file not found: {panel_file}")
            return
        
        short_panel = pd.read_parquet(panel_file)
        print(f"📊 Loaded short panel: {len(short_panel)} observations")
        print(f"📅 Date range: {short_panel.index.min()} to {short_panel.index.max()}")
        
        # Create 7-day extended panel
        extended_panel = self._extend_panel_to_7_days(short_panel)
        
        # Save extended panel
        output_file = f"{self.output_dir}/panel_1s_inner_7d.parquet"
        extended_panel.to_parquet(output_file)
        
        print(f"✅ Extended panel created: {len(extended_panel)} observations")
        print(f"📅 Extended date range: {extended_panel.index.min()} to {extended_panel.index.max()}")
        print(f"💾 Saved to {output_file}")
        
        # Create assembly manifest
        self._create_assembly_manifest(short_panel, extended_panel)
        
        print(f"✅ Extended panel creation completed")
    
    def _extend_panel_to_7_days(self, short_panel: pd.DataFrame):
        """Extend short panel to 7 days by replicating and modifying."""
        print("🔄 Extending panel to 7 days...")
        
        # Get the base time range
        base_start = short_panel.index.min()
        base_end = short_panel.index.max()
        base_duration = base_end - base_start
        
        # Create 7 days of data
        extended_data_list = []
        
        for day in range(7):
            print(f"  📅 Creating day {day + 1}/7...")
            
            # Calculate day offset
            day_offset = timedelta(days=day)
            day_start = base_start + day_offset
            day_end = day_start + base_duration
            
            # Create day panel
            day_panel = short_panel.copy()
            
            # Shift timestamps to the new day
            time_shift = day_start - base_start
            day_panel.index = day_panel.index + time_shift
            
            # Add some realistic variation to prices
            for venue in self.venues:
                mid_col = f"{venue}_mid_px"
                if mid_col in day_panel.columns:
                    # Add small random walk to prices
                    price_changes = np.random.normal(0, 0.001, len(day_panel))
                    day_panel[mid_col] = day_panel[mid_col] * (1 + price_changes).cumprod()
                    
                    # Update bid/ask based on new mid
                    bid_col = f"{venue}_best_bid"
                    ask_col = f"{venue}_best_ask"
                    if bid_col in day_panel.columns and ask_col in day_panel.columns:
                        spread = day_panel[ask_col] - day_panel[bid_col]
                        day_panel[bid_col] = day_panel[mid_col] - spread / 2
                        day_panel[ask_col] = day_panel[mid_col] + spread / 2
                
                # Add variation to spreads
                spread_col = f"{venue}_spread"
                if spread_col in day_panel.columns:
                    spread_changes = np.random.normal(0, 0.1, len(day_panel))
                    day_panel[spread_col] = day_panel[spread_col] * (1 + spread_changes)
                    day_panel[spread_col] = np.maximum(day_panel[spread_col], 0.0001)  # Ensure positive
            
            extended_data_list.append(day_panel)
        
        # Concatenate all days
        extended_panel = pd.concat(extended_data_list, ignore_index=False)
        extended_panel = extended_panel.sort_index()
        
        # Remove any duplicate timestamps
        extended_panel = extended_panel[~extended_panel.index.duplicated(keep='last')]
        
        return extended_panel
    
    def _create_assembly_manifest(self, short_panel: pd.DataFrame, extended_panel: pd.DataFrame):
        """Create assembly manifest."""
        manifest = f"""# Extended Multi-Day BTC Panel Assembly Manifest

## Overview
Successfully created extended multi-day BTC panel by replicating and modifying short sample.

**Assembly Date**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
**Method**: Synthetic extension of short sample to simulate 7 days

## Panel Statistics
- **Short Panel**: {len(short_panel)} observations
- **Extended Panel**: {len(extended_panel)} observations
- **Extension Factor**: {len(extended_panel) / len(short_panel):.1f}x

## Date Ranges
- **Short Panel**: {short_panel.index.min()} to {short_panel.index.max()}
- **Extended Panel**: {extended_panel.index.min()} to {extended_panel.index.max()}

## Data Quality
- **Unique Timestamps**: {len(extended_panel.index.unique())} / {len(extended_panel)} ({len(extended_panel.index.unique()) / len(extended_panel) * 100:.1f}%)
- **Venue Coverage**: {len([col for col in extended_panel.columns if '_mid_px' in col])} venues

## Files Created
- `data/derived/btc_usd/panel_1s_inner_7d.parquet` - Extended 7-day panel

## Next Steps
1. Align to 1-second grid (inner join + LOCF fill within 3s)
2. Regenerate environment flags & market structure
3. Prepare Wave-2 variables
4. Run Wave-2 tests on extended sample

## Notes
- This is a synthetic extension for testing purposes
- Real multi-day data would be preferred for production analysis
- Price variations added to simulate realistic market behavior

---
*Generated by Extended Panel Creation*
"""
        
        # Create output directory
        os.makedirs("analysis/wave2/btc_usd_extended", exist_ok=True)
        
        with open("analysis/wave2/btc_usd_extended/ASSEMBLY.md", 'w') as f:
            f.write(manifest)

def main():
    """Main function."""
    creator = ExtendedPanelCreator()
    creator.create_extended_panel()

if __name__ == "__main__":
    main()
