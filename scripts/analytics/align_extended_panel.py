#!/usr/bin/env python3
"""
Align Extended Panel to 1-Second Grid

Method: For each venue, resample mid to 1s via LOCF with max gap=3s.
Inner join across venues to common timestamps.
Winsorize mid-returns at 1%/99% per venue.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class ExtendedPanelAligner:
    """Align extended panel to 1-second grid."""
    
    def __init__(self):
        self.data_dir = "data/derived/btc_usd"
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        
    def align_extended_panel(self):
        """Align extended panel to 1-second grid."""
        print(f"🔧 Aligning Extended Panel to 1-Second Grid")
        print("=" * 50)
        
        # Load extended panel
        panel_file = f"{self.data_dir}/panel_1s_inner_7d.parquet"
        if not os.path.exists(panel_file):
            print(f"❌ Extended panel file not found: {panel_file}")
            return
        
        extended_panel = pd.read_parquet(panel_file)
        print(f"📊 Loaded extended panel: {len(extended_panel)} observations")
        print(f"📅 Date range: {extended_panel.index.min()} to {extended_panel.index.max()}")
        
        # Align to 1-second grid
        aligned_panel = self._align_to_1s_grid(extended_panel)
        
        # Save aligned panel
        output_file = f"{self.data_dir}/panel_1s_inner_7d_aligned.parquet"
        aligned_panel.to_parquet(output_file)
        
        print(f"✅ Aligned panel created: {len(aligned_panel)} observations")
        print(f"📅 Aligned date range: {aligned_panel.index.min()} to {aligned_panel.index.max()}")
        print(f"💾 Saved to {output_file}")
        
        # Print QC statistics
        self._print_qc_stats(extended_panel, aligned_panel)
        
        print(f"✅ Extended panel alignment completed")
    
    def _align_to_1s_grid(self, panel: pd.DataFrame):
        """Align panel to 1-second grid."""
        print("🔄 Aligning to 1-second grid...")
        
        # Create 1-second grid for the entire time range
        start_time = panel.index.min().floor('S')
        end_time = panel.index.max().ceil('S')
        grid = pd.date_range(start=start_time, end=end_time, freq='1S', tz='UTC')
        
        print(f"  📅 Created 1-second grid: {len(grid)} timestamps")
        
        # Align each venue
        aligned_venues = {}
        
        for venue in self.venues:
            print(f"  🏢 Aligning {venue}...")
            
            # Get venue columns
            venue_cols = [col for col in panel.columns if col.startswith(f"{venue}_")]
            if not venue_cols:
                print(f"    ⚠️ No columns found for {venue}")
                continue
            
            # Create venue dataframe
            venue_data = panel[venue_cols].copy()
            venue_data = venue_data.dropna()
            
            if len(venue_data) == 0:
                print(f"    ⚠️ No data for {venue}")
                continue
            
            # Resample to 1-second grid with LOCF
            venue_aligned = venue_data.reindex(grid, method='ffill', limit=3)
            
            # Check for gaps > 3 seconds
            gap_mask = venue_aligned.index.to_series().diff() > pd.Timedelta(seconds=3)
            venue_aligned.loc[gap_mask, :] = np.nan
            
            aligned_venues[venue] = venue_aligned
            print(f"    ✅ {venue}: {len(venue_aligned)} timestamps, {venue_aligned.isna().sum().sum()} NaN values")
        
        if not aligned_venues:
            print("❌ No venue data to align")
            return pd.DataFrame()
        
        # Inner join across venues
        print("🔄 Performing inner join across venues...")
        
        # Start with first venue
        aligned_panel = aligned_venues[list(aligned_venues.keys())[0]]
        
        # Join with remaining venues
        for venue, venue_data in list(aligned_venues.items())[1:]:
            aligned_panel = aligned_panel.join(venue_data, how='inner', rsuffix=f'_{venue}_temp')
            
            # Remove temporary suffix columns
            temp_cols = [col for col in aligned_panel.columns if col.endswith('_temp')]
            aligned_panel = aligned_panel.drop(columns=temp_cols)
        
        # Winsorize mid-returns at 1%/99% per venue
        print("🔄 Winsorizing mid-returns...")
        
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            if mid_col in aligned_panel.columns:
                # Calculate returns
                returns = aligned_panel[mid_col].pct_change().dropna()
                
                # Winsorize at 1%/99%
                lower_bound = returns.quantile(0.01)
                upper_bound = returns.quantile(0.99)
                
                # Apply winsorization
                returns_winsorized = returns.clip(lower=lower_bound, upper=upper_bound)
                
                # Reconstruct prices from winsorized returns
                aligned_panel[mid_col] = aligned_panel[mid_col].iloc[0] * (1 + returns_winsorized).cumprod()
                
                print(f"    ✅ {venue}: Winsorized {len(returns)} returns")
        
        return aligned_panel
    
    def _print_qc_stats(self, original_panel: pd.DataFrame, aligned_panel: pd.DataFrame):
        """Print QC statistics."""
        print("\n📊 QC Statistics:")
        print("=" * 30)
        
        # Basic stats
        print(f"Original observations: {len(original_panel):,}")
        print(f"Aligned observations: {len(aligned_panel):,}")
        print(f"Retention rate: {len(aligned_panel) / len(original_panel) * 100:.1f}%")
        
        # Time range
        print(f"Original range: {original_panel.index.min()} to {original_panel.index.max()}")
        print(f"Aligned range: {aligned_panel.index.min()} to {aligned_panel.index.max()}")
        
        # Per-venue NaN percentages
        print("\nPer-venue NaN percentages:")
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            if mid_col in aligned_panel.columns:
                nan_pct = aligned_panel[mid_col].isna().sum() / len(aligned_panel) * 100
                print(f"  {venue}: {nan_pct:.1f}%")
        
        # Inner join cost
        original_timestamps = len(original_panel.index.unique())
        aligned_timestamps = len(aligned_panel.index.unique())
        print(f"\nInner join cost: {original_timestamps - aligned_timestamps:,} timestamps dropped")
        print(f"Timestamp retention: {aligned_timestamps / original_timestamps * 100:.1f}%")
        
        # Check if inner join dropped >50% of timestamps
        if aligned_timestamps / original_timestamps < 0.5:
            print("⚠️ WARNING: Inner join dropped >50% of timestamps!")
            print("   This may indicate data quality issues or misaligned timestamps.")
        else:
            print("✅ Inner join retention rate is acceptable")

def main():
    """Main function."""
    aligner = ExtendedPanelAligner()
    aligner.align_extended_panel()

if __name__ == "__main__":
    main()
