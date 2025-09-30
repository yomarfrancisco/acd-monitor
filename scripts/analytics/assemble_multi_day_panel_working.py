#!/usr/bin/env python3
"""
Working Multi-Day Panel Assembly
Fixed timestamp handling and memory-efficient processing.
"""

import boto3
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from pathlib import Path
import json
import sys
from typing import Dict, List, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class WorkingMultiDayPanelAssembler:
    """Working multi-day panel assembler with fixed timestamp handling."""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = 'acd-monitor-snapshots'
        self.btc_prefix = 'snapshots/BTC-USD/'
        self.venues = ['binance', 'coinbase', 'kraken', 'okx', 'bybit']
        self.data_dir = 'data/derived/btc_usd'
        self.analysis_dir = 'analysis/wave2/btc_usd_extended'
        
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.analysis_dir, exist_ok=True)
    
    def assemble_multi_day_panel(self):
        """Assemble multi-day panel with working approach."""
        print("🔧 Working Multi-Day Panel Assembly")
        print("=" * 60)
        
        # Step 1: Get parquet files by date
        print("📥 Organizing parquet files by date...")
        files_by_date = self._organize_files_by_date()
        
        if not files_by_date:
            print("❌ No parquet files found")
            return False
        
        print(f"📊 Found data for {len(files_by_date)} dates")
        for date, files in files_by_date.items():
            print(f"  {date}: {len(files)} files")
        
        # Step 2: Process each date separately and save
        processed_dates = []
        for date, files in files_by_date.items():
            print(f"\n🔄 Processing {date}...")
            date_panel = self._process_single_date(date, files)
            if date_panel is not None and len(date_panel) > 0:
                # Save intermediate result
                intermediate_file = f"{self.data_dir}/panel_1s_{date}.parquet"
                date_panel.to_parquet(intermediate_file)
                processed_dates.append(date)
                print(f"  ✅ {date}: {len(date_panel)} observations saved")
            else:
                print(f"  ⚠️ {date}: No data processed")
        
        if not processed_dates:
            print("❌ No dates processed successfully")
            return False
        
        # Step 3: Load and combine intermediate results
        print(f"\n🔄 Combining {len(processed_dates)} processed dates...")
        all_panels = []
        for date in processed_dates:
            intermediate_file = f"{self.data_dir}/panel_1s_{date}.parquet"
            if os.path.exists(intermediate_file):
                date_panel = pd.read_parquet(intermediate_file)
                all_panels.append(date_panel)
                print(f"  ✅ Loaded {date}: {len(date_panel)} observations")
        
        if not all_panels:
            print("❌ No panels to combine")
            return False
        
        # Combine all panels
        combined_panel = pd.concat(all_panels, ignore_index=False)
        combined_panel = combined_panel.sort_index()
        combined_panel = combined_panel[~combined_panel.index.duplicated(keep='last')]
        
        print(f"✅ Combined panel: {len(combined_panel)} observations")
        print(f"📅 Date range: {combined_panel.index.min()} to {combined_panel.index.max()}")
        
        # Step 4: Apply quality controls
        print("\n🔄 Applying quality controls...")
        cleaned_panel = self._apply_quality_controls(combined_panel)
        
        # Step 5: Save final panel
        panel_file = f"{self.data_dir}/panel_1s_inner_real_multi_day.parquet"
        cleaned_panel.to_parquet(panel_file)
        print(f"💾 Saved final panel to {panel_file}")
        
        # Step 6: Clean up intermediate files
        print("\n🧹 Cleaning up intermediate files...")
        for date in processed_dates:
            intermediate_file = f"{self.data_dir}/panel_1s_{date}.parquet"
            if os.path.exists(intermediate_file):
                os.remove(intermediate_file)
                print(f"  🗑️ Removed {intermediate_file}")
        
        # Step 7: Generate report
        self._generate_assembly_report(cleaned_panel, files_by_date, processed_dates)
        
        print(f"\n✅ Multi-day panel assembly completed")
        return True
    
    def _organize_files_by_date(self):
        """Organize parquet files by date."""
        objects = []
        paginator = self.s3_client.get_paginator('list_objects_v2')
        
        try:
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=self.btc_prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        if obj['Key'].endswith('.parquet'):
                            parts = obj['Key'].split('/')
                            if len(parts) >= 3:
                                date = parts[2]
                                objects.append({
                                    'key': obj['Key'],
                                    'date': date,
                                    'size': obj['Size']
                                })
        except Exception as e:
            print(f"❌ Error listing files: {e}")
            return {}
        
        # Group by date
        files_by_date = {}
        for obj in objects:
            date = obj['date']
            if date not in files_by_date:
                files_by_date[date] = []
            files_by_date[date].append(obj)
        
        return files_by_date
    
    def _process_single_date(self, date: str, files: List[Dict]) -> Optional[pd.DataFrame]:
        """Process all files for a single date."""
        print(f"  📊 Processing {len(files)} files for {date}")
        
        # Group files by venue
        venue_files = {}
        for file_info in files:
            key = file_info['key']
            for venue in self.venues:
                if venue in key:
                    if venue not in venue_files:
                        venue_files[venue] = []
                    venue_files[venue].append(file_info)
                    break
        
        print(f"  📊 Found files for {len(venue_files)} venues")
        
        # Process each venue
        venue_data = {}
        for venue, venue_file_list in venue_files.items():
            print(f"    🔄 Processing {venue} ({len(venue_file_list)} files)...")
            venue_df = self._load_venue_data_single(venue, venue_file_list)
            if venue_df is not None and len(venue_df) > 0:
                venue_data[venue] = venue_df
                print(f"      ✅ {venue}: {len(venue_df)} observations")
            else:
                print(f"      ⚠️ {venue}: No data")
        
        if not venue_data:
            return None
        
        # Align venues to common grid
        print(f"  🔄 Aligning {len(venue_data)} venues...")
        aligned_panel = self._align_venues_to_grid(venue_data)
        
        return aligned_panel
    
    def _load_venue_data_single(self, venue: str, venue_files: List[Dict]) -> Optional[pd.DataFrame]:
        """Load data for a venue (single date)."""
        venue_dfs = []
        
        for file_info in venue_files:
            try:
                # Download and process file
                temp_file = f"/tmp/temp_{venue}_{file_info['key'].split('/')[-1]}"
                
                self.s3_client.download_file(
                    Bucket=self.bucket_name,
                    Key=file_info['key'],
                    Filename=temp_file
                )
                
                df = pd.read_parquet(temp_file)
                
                if len(df) > 0:
                    # Process timestamp - fix the conversion
                    if 'ts_exchange' in df.columns:
                        # Check if it's already a datetime
                        if pd.api.types.is_datetime64_any_dtype(df['ts_exchange']):
                            df['ts'] = df['ts_exchange']
                        else:
                            # Convert from nanoseconds
                            df['ts'] = pd.to_datetime(df['ts_exchange'], unit='ns')
                    else:
                        continue
                    
                    df = df.set_index('ts')
                    
                    # Ensure UTC timezone
                    if df.index.tz is None:
                        df.index = df.index.tz_localize('UTC')
                    else:
                        df.index = df.index.tz_convert('UTC')
                    
                    # Rename columns
                    column_mapping = {
                        'best_bid': f'{venue}_bid_px',
                        'best_ask': f'{venue}_ask_px',
                        'last_px': f'{venue}_last_px',
                        'bid_sz': f'{venue}_bid_sz',
                        'ask_sz': f'{venue}_ask_sz',
                        'trade_sz': f'{venue}_trade_sz'
                    }
                    
                    existing_mapping = {k: v for k, v in column_mapping.items() if k in df.columns}
                    df = df.rename(columns=existing_mapping)
                    
                    # Calculate mid price
                    if f'{venue}_bid_px' in df.columns and f'{venue}_ask_px' in df.columns:
                        df[f'{venue}_mid_px'] = (df[f'{venue}_bid_px'] + df[f'{venue}_ask_px']) / 2
                    elif f'{venue}_last_px' in df.columns:
                        df[f'{venue}_mid_px'] = df[f'{venue}_last_px']
                    
                    venue_dfs.append(df)
                
                # Clean up
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
            except Exception as e:
                print(f"      ⚠️ Error loading {file_info['key']}: {e}")
                continue
        
        if not venue_dfs:
            return None
        
        # Combine and dedupe
        combined_df = pd.concat(venue_dfs, ignore_index=False)
        combined_df = combined_df.sort_index()
        combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
        
        return combined_df
    
    def _align_venues_to_grid(self, venue_data: Dict[str, pd.DataFrame]) -> Optional[pd.DataFrame]:
        """Align venues to common 1-second grid."""
        # Find common time range
        all_timestamps = []
        for df in venue_data.values():
            all_timestamps.extend(df.index.tolist())
        
        if not all_timestamps:
            return None
        
        start_time = min(all_timestamps).floor('S')
        end_time = max(all_timestamps).ceil('S')
        
        # Create 1-second grid
        grid = pd.date_range(start=start_time, end=end_time, freq='1S', tz='UTC')
        
        # Align each venue
        aligned_venues = {}
        for venue, df in venue_data.items():
            aligned_df = df.reindex(grid, method='ffill', limit=3)
            aligned_venues[venue] = aligned_df
        
        # Combine all venues
        combined_panel = pd.concat(aligned_venues.values(), axis=1)
        
        return combined_panel
    
    def _apply_quality_controls(self, panel: pd.DataFrame) -> pd.DataFrame:
        """Apply data quality controls."""
        # Remove duplicate timestamps
        panel = panel[~panel.index.duplicated(keep='last')]
        panel = panel.sort_index()
        
        # Winsorize price columns
        price_columns = [col for col in panel.columns if 'mid_px' in col or 'bid_px' in col or 'ask_px' in col]
        for col in price_columns:
            if col in panel.columns:
                lower_bound = panel[col].quantile(0.01)
                upper_bound = panel[col].quantile(0.99)
                panel[col] = panel[col].clip(lower=lower_bound, upper=upper_bound)
        
        # Remove rows where all mid prices are missing
        mid_price_cols = [col for col in panel.columns if 'mid_px' in col]
        if mid_price_cols:
            panel = panel.dropna(subset=mid_price_cols, how='all')
        
        return panel
    
    def _generate_assembly_report(self, panel: pd.DataFrame, files_by_date: Dict, processed_dates: List[str]):
        """Generate assembly report."""
        report = {
            'assembly_date': datetime.now().isoformat(),
            'total_dates': len(files_by_date),
            'processed_dates': processed_dates,
            'panel_observations': len(panel),
            'panel_columns': len(panel.columns),
            'date_range': {
                'start': str(panel.index.min()),
                'end': str(panel.index.max()),
                'duration_hours': (panel.index.max() - panel.index.min()).total_seconds() / 3600
            },
            'venue_coverage': {},
            'files_by_date': {date: len(files) for date, files in files_by_date.items()}
        }
        
        # Venue coverage
        for venue in self.venues:
            venue_cols = [col for col in panel.columns if col.startswith(f"{venue}_")]
            report['venue_coverage'][venue] = {
                'columns': len(venue_cols),
                'has_mid_px': any('mid_px' in col for col in venue_cols)
            }
        
        # Save report
        with open(f"{self.analysis_dir}/assembly_report.json", 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        with open(f"{self.analysis_dir}/ASSEMBLY_SUMMARY.md", 'w') as f:
            f.write(f"# Real Multi-Day BTC-USD Panel Assembly Report\n\n")
            f.write(f"**Assembly Date**: {report['assembly_date']}\n")
            f.write(f"**Dates Available**: {report['total_dates']}\n")
            f.write(f"**Dates Processed**: {len(report['processed_dates'])}\n")
            f.write(f"**Panel Observations**: {report['panel_observations']:,}\n")
            f.write(f"**Panel Columns**: {report['panel_columns']}\n")
            f.write(f"**Date Range**: {report['date_range']['start']} to {report['date_range']['end']}\n")
            f.write(f"**Duration**: {report['date_range']['duration_hours']:.1f} hours\n\n")
            
            f.write("## Processed Dates\n\n")
            for date in report['processed_dates']:
                f.write(f"- **{date}**: Successfully processed\n")
            
            f.write("\n## Venue Coverage\n\n")
            for venue, coverage in report['venue_coverage'].items():
                f.write(f"- **{venue}**: {coverage['columns']} columns")
                if coverage['has_mid_px']:
                    f.write(" (mid_px ✓)")
                f.write("\n")
            
            f.write("\n## Files by Date\n\n")
            for date, count in report['files_by_date'].items():
                status = "✅ Processed" if date in report['processed_dates'] else "❌ Failed"
                f.write(f"- **{date}**: {count} files ({status})\n")

if __name__ == "__main__":
    assembler = WorkingMultiDayPanelAssembler()
    success = assembler.assemble_multi_day_panel()
    
    if success:
        print("\n🎉 Real multi-day panel assembly completed successfully!")
    else:
        print("\n❌ Panel assembly failed!")
        sys.exit(1)
