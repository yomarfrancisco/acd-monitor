#!/usr/bin/env python3
"""
Fix Copula Marginals - Robust Generation
Generate uniform marginals with hierarchical fallback to avoid empty results.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, List, Optional, Tuple

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class CopulaMarginalsFixer:
    """Fix empty copula marginals with robust generation."""
    
    def __init__(self):
        self.data_dir = 'data/derived/btc_usd'
        self.wave3_dir = f"{self.data_dir}/wave3"
        self.venues = ['binance', 'coinbase', 'kraken', 'okx', 'bybit']
        self.min_obs = 1200  # Minimum observations per session
        
    def fix_copula_marginals(self):
        """Fix copula marginals with robust generation."""
        print("🔧 Fixing Copula Marginals - Robust Generation")
        print("=" * 60)
        
        # Load input data
        print("📥 Loading input data...")
        panel_file = f"{self.data_dir}/panel_1s_inner_real_single_date.parquet"
        env_file = f"{self.data_dir}/env_flags_1s_real_single_date.parquet"
        
        panel = pd.read_parquet(panel_file)
        env_flags = pd.read_parquet(env_file)
        
        print(f"  📊 Panel: {panel.shape}")
        print(f"  📊 Environment flags: {env_flags.shape}")
        
        # Combine data
        combined_data = pd.concat([panel, env_flags], axis=1)
        print(f"  📊 Combined data: {combined_data.shape}")
        
        # Calculate core series
        print("🔄 Calculating core series...")
        data_with_series = self._calculate_core_series(combined_data)
        
        # Generate copula marginals
        print("🔄 Generating copula marginals...")
        copula_data = self._generate_copula_marginals(data_with_series)
        
        if copula_data is None or len(copula_data) == 0:
            print("❌ Failed to generate copula marginals")
            return False
        
        # Sanity checks
        print("🔍 Running sanity checks...")
        if not self._sanity_checks(copula_data):
            print("❌ Sanity checks failed")
            return False
        
        # Save copula marginals
        copula_file = f"{self.wave3_dir}/copula_marginals.parquet"
        copula_data.to_parquet(copula_file)
        print(f"✅ Copula marginals saved: {copula_data.shape}")
        
        return True
    
    def _calculate_core_series(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate core series for copula marginals."""
        data_with_series = data.copy()
        
        # Calculate per-venue returns
        for venue in self.venues:
            mid_col = f'{venue}_mid_px'
            if mid_col in data_with_series.columns:
                # Winsorize returns at 1%/99% before calculating
                mid_prices = data_with_series[mid_col].dropna()
                if len(mid_prices) > 0:
                    lower_bound = mid_prices.quantile(0.01)
                    upper_bound = mid_prices.quantile(0.99)
                    winsorized_prices = mid_prices.clip(lower=lower_bound, upper=upper_bound)
                    data_with_series.loc[winsorized_prices.index, mid_col] = winsorized_prices
                
                # Calculate returns
                data_with_series[f'{venue}_return'] = np.log(data_with_series[mid_col] / data_with_series[mid_col].shift(1))
        
        # Use existing spread columns if available, otherwise calculate
        for venue in self.venues:
            existing_spread_col = f'spread_{venue}'
            if existing_spread_col in data_with_series.columns:
                # Use existing spread column
                data_with_series[f'{venue}_spread'] = data_with_series[existing_spread_col]
            else:
                # Calculate from bid/ask
                bid_col = f'{venue}_bid_px'
                ask_col = f'{venue}_ask_px'
                if bid_col in data_with_series.columns and ask_col in data_with_series.columns:
                    data_with_series[f'{venue}_spread'] = data_with_series[ask_col] - data_with_series[bid_col]
        
        # Calculate cross-venue dispersion
        mid_cols = [f'{venue}_mid_px' for venue in self.venues if f'{venue}_mid_px' in data_with_series.columns]
        if mid_cols:
            data_with_series['dispersion'] = data_with_series[mid_cols].max(axis=1) - data_with_series[mid_cols].min(axis=1)
        
        return data_with_series
    
    def _generate_copula_marginals(self, data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Generate copula marginals with hierarchical fallback."""
        print("  🔄 Analyzing session structure...")
        
        # Check session distribution
        if 'session_label' not in data.columns:
            print("  ❌ No session_label column found")
            return None
        
        session_counts = data['session_label'].value_counts()
        print(f"  📊 Session distribution: {dict(session_counts)}")
        
        # Determine partitioning strategy
        use_session_partition = True
        for session in ['Asia', 'Europe', 'US', 'Pacific']:
            if session in session_counts.index and session_counts[session] < self.min_obs:
                print(f"  ⚠️ Session {session} has {session_counts[session]} obs < {self.min_obs}, using whole-day fallback")
                use_session_partition = False
                break
        
        if not use_session_partition:
            print("  🔄 Using whole-day fallback partitioning")
            return self._generate_whole_day_marginals(data)
        else:
            print("  🔄 Using session-based partitioning")
            return self._generate_session_marginals(data)
    
    def _generate_session_marginals(self, data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Generate marginals partitioned by session."""
        all_marginals = []
        
        for session in ['Asia', 'Europe', 'US', 'Pacific']:
            session_mask = data['session_label'] == session
            session_data = data[session_mask]
            
            if len(session_data) == 0:
                continue
            
            print(f"    📊 Processing session {session}: {len(session_data)} observations")
            
            # Generate marginals for this session
            session_marginals = self._generate_marginals_for_partition(session_data, session)
            if session_marginals is not None and len(session_marginals) > 0:
                all_marginals.append(session_marginals)
        
        if not all_marginals:
            print("  ❌ No session marginals generated")
            return None
        
        # Combine all session marginals
        combined_marginals = pd.concat(all_marginals, ignore_index=False)
        combined_marginals = combined_marginals.sort_index()
        
        print(f"  ✅ Session marginals combined: {combined_marginals.shape}")
        return combined_marginals
    
    def _generate_whole_day_marginals(self, data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Generate marginals using whole-day partitioning."""
        print("    📊 Processing whole-day data: {len(data)} observations")
        
        # Generate marginals for whole day
        whole_day_marginals = self._generate_marginals_for_partition(data, 'whole_day')
        
        if whole_day_marginals is None or len(whole_day_marginals) == 0:
            print("  ❌ No whole-day marginals generated")
            return None
        
        print(f"  ✅ Whole-day marginals: {whole_day_marginals.shape}")
        return whole_day_marginals
    
    def _generate_marginals_for_partition(self, partition_data: pd.DataFrame, partition_name: str) -> Optional[pd.DataFrame]:
        """Generate marginals for a specific partition."""
        marginals_data = []
        
        # Process in 15-minute chunks for memory safety
        chunk_size = pd.Timedelta('15T')
        start_time = partition_data.index.min()
        end_time = partition_data.index.max()
        
        current_start = start_time
        while current_start < end_time:
            current_end = min(current_start + chunk_size, end_time)
            chunk_data = partition_data.loc[current_start:current_end]
            
            if len(chunk_data) > 0:
                chunk_marginals = self._process_chunk_marginals(chunk_data, partition_name)
                if chunk_marginals is not None and len(chunk_marginals) > 0:
                    marginals_data.append(chunk_marginals)
            
            current_start = current_end
        
        if not marginals_data:
            return None
        
        # Combine chunk marginals
        combined_marginals = pd.concat(marginals_data, ignore_index=False)
        return combined_marginals
    
    def _process_chunk_marginals(self, chunk_data: pd.DataFrame, partition_name: str) -> Optional[pd.DataFrame]:
        """Process marginals for a single chunk."""
        chunk_marginals = pd.DataFrame(index=chunk_data.index)
        chunk_marginals['ts'] = chunk_data.index
        chunk_marginals['session_label'] = partition_name if partition_name != 'whole_day' else chunk_data['session_label'].iloc[0] if 'session_label' in chunk_data.columns else 'unknown'
        
        # Process per-venue returns
        for venue in self.venues:
            return_col = f'{venue}_return'
            if return_col in chunk_data.columns:
                returns = chunk_data[return_col].dropna()
                if len(returns) > 0:
                    ranks = returns.rank(method='average')
                    u_values = ranks / (len(ranks) + 1)
                    chunk_marginals.loc[returns.index, f'u_ret_{venue}'] = u_values
        
        # Process per-venue spreads
        for venue in self.venues:
            spread_col = f'{venue}_spread'
            if spread_col in chunk_data.columns:
                spreads = chunk_data[spread_col].dropna()
                if len(spreads) > 0:
                    ranks = spreads.rank(method='average')
                    u_values = ranks / (len(ranks) + 1)
                    chunk_marginals.loc[spreads.index, f'u_spr_{venue}'] = u_values
        
        # Process cross-venue dispersion
        if 'dispersion' in chunk_data.columns:
            dispersion = chunk_data['dispersion'].dropna()
            if len(dispersion) > 0:
                ranks = dispersion.rank(method='average')
                u_values = ranks / (len(ranks) + 1)
                chunk_marginals.loc[dispersion.index, 'u_dispersion'] = u_values
        
        # Drop rows with all missing marginals
        marginal_cols = [col for col in chunk_marginals.columns if col.startswith('u_')]
        if marginal_cols:
            chunk_marginals = chunk_marginals.dropna(subset=marginal_cols, how='all')
        
        return chunk_marginals if len(chunk_marginals) > 0 else None
    
    def _sanity_checks(self, copula_data: pd.DataFrame) -> bool:
        """Run sanity checks on copula marginals."""
        print("  🔍 Running sanity checks...")
        
        # Check minimum row count
        if len(copula_data) < 5000:
            print(f"    ❌ Insufficient rows: {len(copula_data)} < 5000")
            return False
        
        # Check venue coverage
        ret_cols = [col for col in copula_data.columns if col.startswith('u_ret_')]
        if len(ret_cols) < 3:
            print(f"    ❌ Insufficient venues: {len(ret_cols)} < 3")
            return False
        
        # Check uniform distribution properties
        for col in ret_cols:
            if col in copula_data.columns:
                u_values = copula_data[col].dropna()
                if len(u_values) > 0:
                    min_u = u_values.min()
                    max_u = u_values.max()
                    if min_u <= 0 or max_u >= 1:
                        print(f"    ❌ Invalid uniform range for {col}: [{min_u}, {max_u}]")
                        return False
        
        print("    ✅ All sanity checks passed")
        return True

if __name__ == "__main__":
    fixer = CopulaMarginalsFixer()
    success = fixer.fix_copula_marginals()
    
    if success:
        print("\n🎉 Copula marginals fixed successfully!")
    else:
        print("\n❌ Copula marginals fix failed!")
        sys.exit(1)
