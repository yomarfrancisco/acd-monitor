#!/usr/bin/env python3
"""
Wave-3 Variables Preparation (Variables-Only)
Prepare variables for ICP, VMM, copulas, clustering, and composite index methods.
No model execution - only variable preparation.
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

class Wave3VariablesPreparer:
    """Prepare Wave-3 variables without model execution."""
    
    def __init__(self):
        self.data_dir = 'data/derived/btc_usd'
        self.wave3_dir = f"{self.data_dir}/wave3"
        self.analysis_dir = 'analysis/wave3/btc_usd'
        self.venues = ['binance', 'coinbase', 'kraken', 'okx', 'bybit']
        
        os.makedirs(self.wave3_dir, exist_ok=True)
        os.makedirs(self.analysis_dir, exist_ok=True)
    
    def prepare_all_variables(self):
        """Prepare all Wave-3 variables."""
        print("🔧 Wave-3 Variables Preparation (Variables-Only)")
        print("=" * 60)
        
        # Step 1: Load and prepare core series
        print("\n📥 Loading core series...")
        core_data = self._load_core_series()
        if core_data is None:
            print("❌ Failed to load core series")
            return False
        
        # Step 2: Build ICP design matrix
        print("\n🔄 Building ICP design matrix...")
        icp_success = self._build_icp_design(core_data)
        
        # Step 3: Build VMM moment set
        print("\n🔄 Building VMM moment set...")
        vmm_success = self._build_vmm_moments(core_data)
        
        # Step 4: Prepare copula marginals
        print("\n🔄 Preparing copula marginals...")
        copula_success = self._prepare_copula_marginals(core_data)
        
        # Step 5: Prepare clustering features
        print("\n🔄 Preparing clustering features...")
        clustering_success = self._prepare_clustering_features(core_data)
        
        # Step 6: Prepare composite index inputs
        print("\n🔄 Preparing composite index inputs...")
        composite_success = self._prepare_composite_inputs(core_data)
        
        # Step 7: Generate summary
        print("\n📊 Generating summary...")
        self._generate_summary()
        
        # Check all steps
        all_success = all([icp_success, vmm_success, copula_success, clustering_success, composite_success])
        
        if all_success:
            print("\n✅ Wave-3 variables preparation completed successfully!")
            return True
        else:
            print("\n❌ Some Wave-3 variables preparation failed!")
            return False
    
    def _load_core_series(self) -> Optional[pd.DataFrame]:
        """Load and prepare core series from existing data."""
        try:
            # Load panel data
            panel_file = f"{self.data_dir}/panel_1s_inner_real_single_date.parquet"
            panel = pd.read_parquet(panel_file)
            print(f"  📊 Panel loaded: {panel.shape}")
            
            # Load environment flags
            env_file = f"{self.data_dir}/env_flags_1s_real_single_date.parquet"
            env_flags = pd.read_parquet(env_file)
            print(f"  📊 Environment flags loaded: {env_flags.shape}")
            
            # Load market structure
            structure_file = f"{self.data_dir}/market_structure_real_single_date.parquet"
            market_structure = pd.read_parquet(structure_file)
            print(f"  📊 Market structure loaded: {market_structure.shape}")
            
            # Broadcast market structure to 1-second grid
            market_structure_1s = market_structure.reindex(panel.index, method='ffill')
            
            # Combine all data
            combined_data = pd.concat([panel, env_flags, market_structure_1s], axis=1)
            
            # Calculate core series
            core_data = self._calculate_core_series(combined_data)
            
            print(f"  ✅ Core series prepared: {core_data.shape}")
            return core_data
            
        except Exception as e:
            print(f"  ❌ Error loading core series: {e}")
            return None
    
    def _calculate_core_series(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate core series for Wave-3 analysis."""
        core_data = data.copy()
        
        # Calculate per-venue returns
        for venue in self.venues:
            mid_col = f'{venue}_mid_px'
            if mid_col in core_data.columns:
                core_data[f'{venue}_return'] = np.log(core_data[mid_col] / core_data[mid_col].shift(1))
        
        # Calculate equal-weighted mid and spread
        mid_cols = [f'{venue}_mid_px' for venue in self.venues if f'{venue}_mid_px' in core_data.columns]
        spread_cols = [f'spread_{venue}' for venue in self.venues if f'spread_{venue}' in core_data.columns]
        
        if mid_cols:
            core_data['mid_eq'] = core_data[mid_cols].mean(axis=1)
            core_data['mid_eq_return'] = np.log(core_data['mid_eq'] / core_data['mid_eq'].shift(1))
        
        if spread_cols:
            core_data['spread_eq'] = core_data[spread_cols].mean(axis=1)
        
        # Calculate cross-venue dispersion
        if mid_cols:
            core_data['dispersion'] = core_data[mid_cols].max(axis=1) - core_data[mid_cols].min(axis=1)
        
        # Calculate lead/lag basis
        for venue in self.venues:
            mid_col = f'{venue}_mid_px'
            if mid_col in core_data.columns and 'mid_eq' in core_data.columns:
                core_data[f'{venue}_basis'] = core_data[mid_col] - core_data['mid_eq']
        
        return core_data
    
    def _build_icp_design(self, data: pd.DataFrame) -> bool:
        """Build ICP design matrix (variables-only)."""
        try:
            # Prepare response variable
            icp_data = pd.DataFrame(index=data.index)
            icp_data['ts'] = data.index
            icp_data['Y'] = data['mid_eq_return'].shift(-1)  # Next-tick return
            
            # Prepare predictors (current and lagged)
            for venue in self.venues:
                if f'{venue}_return' in data.columns:
                    icp_data[f'{venue}_return_0'] = data[f'{venue}_return']
                    icp_data[f'{venue}_return_1'] = data[f'{venue}_return'].shift(1)
                    icp_data[f'{venue}_return_5'] = data[f'{venue}_return'].shift(5)
                
                if f'spread_{venue}' in data.columns:
                    icp_data[f'{venue}_spread'] = data[f'spread_{venue}']
                    icp_data[f'{venue}_spread_change'] = data[f'spread_{venue}'].diff()
                
                if f'{venue}_basis' in data.columns:
                    icp_data[f'{venue}_basis'] = data[f'{venue}_basis']
            
            # Add cross-venue dispersion
            if 'dispersion' in data.columns:
                icp_data['dispersion'] = data['dispersion']
            
            # Add environment indicators
            env_cols = ['session_label', 'is_session_transition', 'is_ny_open', 'is_vwap_reset_window']
            for col in env_cols:
                if col in data.columns:
                    icp_data[col] = data[col]
            
            # Add per-venue shock flags
            for venue in self.venues:
                shock_col = f'is_return_2sigma_{venue}'
                vwap_col = f'is_vwap_dev_2sigma_{venue}'
                if shock_col in data.columns:
                    icp_data[shock_col] = data[shock_col]
                if vwap_col in data.columns:
                    icp_data[vwap_col] = data[vwap_col]
            
            # Add structure state
            if 'structure_state' in data.columns:
                icp_data['structure_state'] = data['structure_state']
            
            # Add BOS counts (rolling 10-minute windows)
            if 'bos_up' in data.columns and 'bos_dn' in data.columns:
                icp_data['BOS_up_count_10m'] = data['bos_up'].rolling('10T').sum()
                icp_data['BOS_down_count_10m'] = data['bos_dn'].rolling('10T').sum()
            
            # Add venue count
            venue_count = 0
            for venue in self.venues:
                if f'{venue}_mid_px' in data.columns:
                    venue_count += 1
            icp_data['available_venue_count'] = venue_count
            
            # Drop rows with missing Y
            icp_data = icp_data.dropna(subset=['Y'])
            
            # Save ICP design matrix
            icp_file = f"{self.wave3_dir}/icp_design.parquet"
            icp_data.to_parquet(icp_file)
            print(f"  ✅ ICP design matrix saved: {icp_data.shape}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error building ICP design: {e}")
            return False
    
    def _build_vmm_moments(self, data: pd.DataFrame) -> bool:
        """Build VMM moment set (variables-only)."""
        try:
            # Define 30-minute windows with 5-minute advances
            start_time = data.index.min()
            end_time = data.index.max()
            window_duration = pd.Timedelta('30T')
            advance_duration = pd.Timedelta('5T')
            
            moments_data = []
            current_start = start_time
            
            while current_start + window_duration <= end_time:
                current_end = current_start + window_duration
                window_data = data.loc[current_start:current_end]
                
                if len(window_data) > 0:
                    moment_row = {
                        'window_start': current_start,
                        'window_end': current_end,
                        'n_obs': len(window_data)
                    }
                    
                    # Calculate moments
                    if 'spread_eq' in window_data.columns:
                        moment_row['spread_eq_mean'] = window_data['spread_eq'].mean()
                        moment_row['spread_eq_var'] = window_data['spread_eq'].var()
                    
                    # Per-venue spread moments
                    for venue in self.venues:
                        spread_col = f'spread_{venue}'
                        if spread_col in window_data.columns:
                            moment_row[f'{venue}_spread_mean'] = window_data[spread_col].mean()
                            moment_row[f'{venue}_spread_var'] = window_data[spread_col].var()
                    
                    # Cross-venue return covariances
                    return_cols = [f'{venue}_return' for venue in self.venues if f'{venue}_return' in window_data.columns]
                    if len(return_cols) > 1:
                        return_data = window_data[return_cols].dropna()
                        if len(return_data) > 1:
                            cov_matrix = return_data.cov()
                            for i, col1 in enumerate(return_cols):
                                for j, col2 in enumerate(return_cols):
                                    if i <= j:  # Only upper triangle
                                        moment_row[f'cov_{col1}_{col2}'] = cov_matrix.loc[col1, col2]
                    
                    # Price-lead moments
                    if 'mid_eq_return' in window_data.columns:
                        for venue in self.venues:
                            mid_col = f'{venue}_mid_px'
                            if mid_col in window_data.columns:
                                price_lead = (window_data[mid_col] - window_data['mid_eq'].shift(1)) * window_data['mid_eq_return']
                                moment_row[f'{venue}_price_lead'] = price_lead.mean()
                    
                    # Error correction moments
                    for venue in self.venues:
                        basis_col = f'{venue}_basis'
                        if basis_col in window_data.columns:
                            ec_data = window_data[basis_col].dropna()
                            if len(ec_data) > 0:
                                moment_row[f'{venue}_ec_mean'] = ec_data.mean()
                                moment_row[f'{venue}_ec_var'] = ec_data.var()
                                moment_row[f'{venue}_ec_change_mean'] = ec_data.diff().mean()
                    
                    # Add instruments
                    if 'session_label' in window_data.columns:
                        moment_row['session_asia'] = (window_data['session_label'] == 'asia').sum()
                        moment_row['session_europe'] = (window_data['session_label'] == 'europe').sum()
                        moment_row['session_us'] = (window_data['session_label'] == 'us').sum()
                        moment_row['session_pacific'] = (window_data['session_label'] == 'pacific').sum()
                    
                    # Shock flags
                    for venue in self.venues:
                        shock_col = f'is_return_2sigma_{venue}'
                        vwap_col = f'is_vwap_dev_2sigma_{venue}'
                        if shock_col in window_data.columns:
                            moment_row[f'{venue}_shock_count'] = window_data[shock_col].sum()
                        if vwap_col in window_data.columns:
                            moment_row[f'{venue}_vwap_count'] = window_data[vwap_col].sum()
                    
                    # NY open and structure state
                    if 'is_ny_open' in window_data.columns:
                        moment_row['ny_open_count'] = window_data['is_ny_open'].sum()
                    
                    if 'structure_state' in window_data.columns:
                        moment_row['structure_up_count'] = (window_data['structure_state'] == 'up').sum()
                        moment_row['structure_down_count'] = (window_data['structure_state'] == 'down').sum()
                    
                    moments_data.append(moment_row)
                
                current_start += advance_duration
            
            # Convert to DataFrame and save
            vmm_df = pd.DataFrame(moments_data)
            vmm_file = f"{self.wave3_dir}/vmm_moments.parquet"
            vmm_df.to_parquet(vmm_file)
            print(f"  ✅ VMM moments saved: {vmm_df.shape}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error building VMM moments: {e}")
            return False
    
    def _prepare_copula_marginals(self, data: pd.DataFrame) -> bool:
        """Prepare copula marginals (variables-only)."""
        try:
            copula_data = pd.DataFrame(index=data.index)
            copula_data['ts'] = data.index
            copula_data['session_label'] = data['session_label']
            
            # Calculate uniform marginals for each session
            for session in ['asia', 'europe', 'us', 'pacific']:
                session_mask = data['session_label'] == session
                session_data = data[session_mask]
                
                if len(session_data) > 0:
                    # Per-venue returns
                    for venue in self.venues:
                        return_col = f'{venue}_return'
                        if return_col in session_data.columns:
                            returns = session_data[return_col].dropna()
                            if len(returns) > 0:
                                ranks = returns.rank()
                                u_values = ranks / (len(ranks) + 1)
                                copula_data.loc[session_mask, f'u_ret_{venue}'] = u_values
                    
                    # Per-venue spreads
                    for venue in self.venues:
                        spread_col = f'spread_{venue}'
                        if spread_col in session_data.columns:
                            spreads = session_data[spread_col].dropna()
                            if len(spreads) > 0:
                                ranks = spreads.rank()
                                u_values = ranks / (len(ranks) + 1)
                                copula_data.loc[session_mask, f'u_spr_{venue}'] = u_values
                    
                    # Cross-venue dispersion
                    if 'dispersion' in session_data.columns:
                        dispersion = session_data['dispersion'].dropna()
                        if len(dispersion) > 0:
                            ranks = dispersion.rank()
                            u_values = ranks / (len(ranks) + 1)
                            copula_data.loc[session_mask, 'u_dispersion'] = u_values
            
            # Drop rows with all missing marginals
            marginal_cols = [col for col in copula_data.columns if col.startswith('u_')]
            copula_data = copula_data.dropna(subset=marginal_cols, how='all')
            
            # Save copula marginals
            copula_file = f"{self.wave3_dir}/copula_marginals.parquet"
            copula_data.to_parquet(copula_file)
            print(f"  ✅ Copula marginals saved: {copula_data.shape}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error preparing copula marginals: {e}")
            return False
    
    def _prepare_clustering_features(self, data: pd.DataFrame) -> bool:
        """Prepare clustering feature matrix (variables-only)."""
        try:
            # Define 5-minute non-overlapping windows
            start_time = data.index.min()
            end_time = data.index.max()
            window_duration = pd.Timedelta('5T')
            
            features_data = []
            current_start = start_time
            
            while current_start + window_duration <= end_time:
                current_end = current_start + window_duration
                window_data = data.loc[current_start:current_end]
                
                if len(window_data) > 0:
                    feature_row = {
                        'window_start': current_start,
                        'window_end': current_end,
                        'session_label': window_data['session_label'].iloc[0] if 'session_label' in window_data.columns else 'unknown'
                    }
                    
                    # Per-venue return features
                    for venue in self.venues:
                        return_col = f'{venue}_return'
                        if return_col in window_data.columns:
                            returns = window_data[return_col].dropna()
                            if len(returns) > 0:
                                feature_row[f'{venue}_return_mean'] = returns.mean()
                                feature_row[f'{venue}_return_std'] = returns.std()
                    
                    # Per-venue spread features
                    for venue in self.venues:
                        spread_col = f'spread_{venue}'
                        if spread_col in window_data.columns:
                            spreads = window_data[spread_col].dropna()
                            if len(spreads) > 0:
                                feature_row[f'{venue}_spread_mean'] = spreads.mean()
                                feature_row[f'{venue}_spread_std'] = spreads.std()
                    
                    # Cross-venue dispersion features
                    if 'dispersion' in window_data.columns:
                        dispersion = window_data['dispersion'].dropna()
                        if len(dispersion) > 0:
                            feature_row['dispersion_mean'] = dispersion.mean()
                            feature_row['dispersion_95th'] = dispersion.quantile(0.95)
                    
                    # Event intensities
                    for venue in self.venues:
                        shock_col = f'is_return_2sigma_{venue}'
                        vwap_col = f'is_vwap_dev_2sigma_{venue}'
                        if shock_col in window_data.columns:
                            feature_row[f'{venue}_shock_count'] = window_data[shock_col].sum()
                        if vwap_col in window_data.columns:
                            feature_row[f'{venue}_vwap_count'] = window_data[vwap_col].sum()
                    
                    # Structure counts
                    if 'bos_up' in window_data.columns:
                        feature_row['BOS_up_count'] = window_data['bos_up'].sum()
                    if 'bos_dn' in window_data.columns:
                        feature_row['BOS_down_count'] = window_data['bos_dn'].sum()
                    
                    # Structure state percentages
                    if 'structure_state' in window_data.columns:
                        total = len(window_data)
                        feature_row['structure_up_pct'] = (window_data['structure_state'] == 'up').sum() / total
                        feature_row['structure_down_pct'] = (window_data['structure_state'] == 'down').sum() / total
                        feature_row['structure_neutral_pct'] = (window_data['structure_state'] == 'neutral').sum() / total
                    
                    features_data.append(feature_row)
                
                current_start += window_duration
            
            # Convert to DataFrame
            features_df = pd.DataFrame(features_data)
            
            # Standardize features (z-score within the day)
            numeric_cols = features_df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                if col not in ['window_start', 'window_end']:
                    mean_val = features_df[col].mean()
                    std_val = features_df[col].std()
                    if std_val > 0:
                        features_df[f'{col}_zscore'] = (features_df[col] - mean_val) / std_val
                    else:
                        features_df[f'{col}_zscore'] = 0
            
            # Save clustering features
            clustering_file = f"{self.wave3_dir}/clustering_features.parquet"
            features_df.to_parquet(clustering_file)
            print(f"  ✅ Clustering features saved: {features_df.shape}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error preparing clustering features: {e}")
            return False
    
    def _prepare_composite_inputs(self, data: pd.DataFrame) -> bool:
        """Prepare composite index inputs (variables-only)."""
        try:
            # Define 5-minute windows
            start_time = data.index.min()
            end_time = data.index.max()
            window_duration = pd.Timedelta('5T')
            
            composite_data = []
            current_start = start_time
            
            while current_start + window_duration <= end_time:
                current_end = current_start + window_duration
                window_data = data.loc[current_start:current_end]
                
                if len(window_data) > 0:
                    composite_row = {
                        'window_start': current_start,
                        'window_end': current_end
                    }
                    
                    # Cross-venue dispersion
                    if 'dispersion' in window_data.columns:
                        dispersion = window_data['dispersion'].dropna()
                        if len(dispersion) > 0:
                            composite_row['dispersion_mean'] = dispersion.mean()
                            composite_row['dispersion_95th'] = dispersion.quantile(0.95)
                    
                    # Average spread by venue
                    spread_cols = [f'spread_{venue}' for venue in self.venues if f'spread_{venue}' in window_data.columns]
                    if spread_cols:
                        spreads = window_data[spread_cols].mean(axis=1)
                        composite_row['spread_mean'] = spreads.mean()
                        composite_row['spread_95th'] = spreads.quantile(0.95)
                    
                    # Event intensities (equal-weighted)
                    shock_counts = []
                    vwap_counts = []
                    for venue in self.venues:
                        shock_col = f'is_return_2sigma_{venue}'
                        vwap_col = f'is_vwap_dev_2sigma_{venue}'
                        if shock_col in window_data.columns:
                            shock_counts.append(window_data[shock_col].sum())
                        if vwap_col in window_data.columns:
                            vwap_counts.append(window_data[vwap_col].sum())
                    
                    if shock_counts:
                        composite_row['shock_intensity'] = np.mean(shock_counts)
                    if vwap_counts:
                        composite_row['vwap_intensity'] = np.mean(vwap_counts)
                    
                    # Structure instability
                    if 'bos_up' in window_data.columns and 'bos_dn' in window_data.columns:
                        composite_row['structure_instability'] = window_data['bos_up'].sum() + window_data['bos_dn'].sum()
                    
                    composite_data.append(composite_row)
                
                current_start += window_duration
            
            # Convert to DataFrame
            composite_df = pd.DataFrame(composite_data)
            
            # Z-score standardization
            numeric_cols = composite_df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                if col not in ['window_start', 'window_end']:
                    mean_val = composite_df[col].mean()
                    std_val = composite_df[col].std()
                    if std_val > 0:
                        composite_df[f'{col}_zscore'] = (composite_df[col] - mean_val) / std_val
                    else:
                        composite_df[f'{col}_zscore'] = 0
            
            # Save composite inputs
            composite_file = f"{self.wave3_dir}/composite_inputs.parquet"
            composite_df.to_parquet(composite_file)
            print(f"  ✅ Composite inputs saved: {composite_df.shape}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error preparing composite inputs: {e}")
            return False
    
    def _generate_summary(self):
        """Generate Wave-3 variables summary."""
        summary_file = f"{self.analysis_dir}/WAVE3_VARIABLES_SUMMARY.md"
        
        with open(summary_file, 'w') as f:
            f.write("# Wave-3 Variables Summary\n\n")
            f.write(f"**Generated**: {datetime.now().isoformat()}\n")
            f.write("**Purpose**: Variables-only preparation for Wave-3 methods (ICP, VMM, copulas, clustering, composite index)\n\n")
            
            # Check each file
            files_to_check = [
                'icp_design.parquet',
                'vmm_moments.parquet', 
                'copula_marginals.parquet',
                'clustering_features.parquet',
                'composite_inputs.parquet'
            ]
            
            f.write("## File Summary\n\n")
            for filename in files_to_check:
                filepath = f"{self.wave3_dir}/{filename}"
                if os.path.exists(filepath):
                    df = pd.read_parquet(filepath)
                    f.write(f"### {filename}\n")
                    f.write(f"- **Rows**: {len(df):,}\n")
                    f.write(f"- **Columns**: {len(df.columns)}\n")
                    f.write(f"- **Non-missing %**: {df.notna().mean().mean():.1%}\n")
                    f.write(f"- **Sample columns**: {list(df.columns)[:5]}...\n\n")
                else:
                    f.write(f"### {filename}\n")
                    f.write("- **Status**: ❌ File not found\n\n")
            
            f.write("## Usage Notes\n\n")
            f.write("- **ICP Design**: Ready for ICP model fitting with environment partitions\n")
            f.write("- **VMM Moments**: Ready for VMM model fitting with instruments\n")
            f.write("- **Copula Marginals**: Ready for copula fitting with uniform marginals\n")
            f.write("- **Clustering Features**: Ready for clustering analysis with standardized features\n")
            f.write("- **Composite Inputs**: Ready for composite index construction\n\n")
            
            f.write("## Next Steps\n\n")
            f.write("1. **ICP Model**: Fit ICP models on design matrix\n")
            f.write("2. **VMM Model**: Fit VMM models on moment set\n")
            f.write("3. **Copula Analysis**: Fit copulas on marginals\n")
            f.write("4. **Clustering**: Run clustering algorithms on features\n")
            f.write("5. **Composite Index**: Construct coordination index from inputs\n")

if __name__ == "__main__":
    preparer = Wave3VariablesPreparer()
    success = preparer.prepare_all_variables()
    
    if success:
        print("\n🎉 Wave-3 variables preparation completed successfully!")
    else:
        print("\n❌ Wave-3 variables preparation failed!")
        sys.exit(1)
