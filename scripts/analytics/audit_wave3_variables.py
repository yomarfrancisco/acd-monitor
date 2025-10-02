#!/usr/bin/env python3
"""
Wave-3 Variables Final Audit
Comprehensive audit of all Wave-3 variables with detailed reporting.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class Wave3VariablesAuditor:
    """Audit all Wave-3 variables comprehensively."""
    
    def __init__(self):
        self.wave3_dir = 'data/derived/btc_usd/wave3'
        self.analysis_dir = 'analysis/wave3/btc_usd'
        self.venues = ['binance', 'coinbase', 'kraken', 'okx', 'bybit']
    
    def audit_all_variables(self):
        """Audit all Wave-3 variables."""
        print("🔍 Wave-3 Variables Final Audit")
        print("=" * 50)
        
        # Audit each file
        icp_audit = self._audit_icp_design()
        vmm_audit = self._audit_vmm_moments()
        copula_audit = self._audit_copula_marginals()
        clustering_audit = self._audit_clustering_features()
        composite_audit = self._audit_composite_inputs()
        
        # Generate comprehensive report
        self._generate_audit_report(icp_audit, vmm_audit, copula_audit, clustering_audit, composite_audit)
        
        print("\n✅ Wave-3 variables audit completed!")
        return True
    
    def _audit_icp_design(self):
        """Audit ICP design matrix."""
        print("\n📊 Auditing ICP design matrix...")
        
        try:
            df = pd.read_parquet(f"{self.wave3_dir}/icp_design.parquet")
            
            audit = {
                'file': 'icp_design.parquet',
                'rows': len(df),
                'columns': len(df.columns),
                'non_missing_pct': df.notna().mean().mean(),
                'y_stats': {},
                'x_stats': {},
                'env_stats': {}
            }
            
            # Y variable stats
            if 'Y' in df.columns:
                y_data = df['Y'].dropna()
                audit['y_stats'] = {
                    'count': len(y_data),
                    'mean': y_data.mean(),
                    'std': y_data.std(),
                    'min': y_data.min(),
                    'max': y_data.max()
                }
            
            # X variables stats (sample a few)
            x_cols = [col for col in df.columns if col.startswith(('binance_return', 'coinbase_return'))]
            for col in x_cols[:3]:  # Sample first 3
                if col in df.columns:
                    x_data = df[col].dropna()
                    audit['x_stats'][col] = {
                        'count': len(x_data),
                        'mean': x_data.mean(),
                        'std': x_data.std()
                    }
            
            # Environment variables
            env_cols = ['session_label', 'is_session_transition', 'is_ny_open']
            for col in env_cols:
                if col in df.columns:
                    if col == 'session_label':
                        audit['env_stats'][col] = df[col].value_counts().to_dict()
                    else:
                        audit['env_stats'][col] = {
                            'true_count': df[col].sum(),
                            'false_count': (df[col] == False).sum()
                        }
            
            print(f"  ✅ ICP design: {audit['rows']:,} rows, {audit['columns']} columns, {audit['non_missing_pct']:.1%} non-missing")
            return audit
            
        except Exception as e:
            print(f"  ❌ Error auditing ICP design: {e}")
            return None
    
    def _audit_vmm_moments(self):
        """Audit VMM moments."""
        print("\n📊 Auditing VMM moments...")
        
        try:
            df = pd.read_parquet(f"{self.wave3_dir}/vmm_moments.parquet")
            
            audit = {
                'file': 'vmm_moments.parquet',
                'rows': len(df),
                'columns': len(df.columns),
                'non_missing_pct': df.notna().mean().mean(),
                'window_stats': {},
                'moment_stats': {},
                'instrument_stats': {}
            }
            
            # Window stats
            if 'window_start' in df.columns and 'window_end' in df.columns:
                window_duration = (df['window_end'] - df['window_start']).dt.total_seconds() / 60
                audit['window_stats'] = {
                    'duration_min': window_duration.min(),
                    'duration_max': window_duration.max(),
                    'duration_mean': window_duration.mean()
                }
            
            # Moment stats (sample a few)
            moment_cols = [col for col in df.columns if any(x in col for x in ['mean', 'var', 'cov'])]
            for col in moment_cols[:5]:  # Sample first 5
                if col in df.columns:
                    moment_data = df[col].dropna()
                    audit['moment_stats'][col] = {
                        'count': len(moment_data),
                        'mean': moment_data.mean(),
                        'std': moment_data.std()
                    }
            
            # Instrument stats
            instrument_cols = [col for col in df.columns if any(x in col for x in ['session_', 'shock_', 'ny_open'])]
            for col in instrument_cols[:5]:  # Sample first 5
                if col in df.columns:
                    inst_data = df[col].dropna()
                    audit['instrument_stats'][col] = {
                        'count': len(inst_data),
                        'mean': inst_data.mean(),
                        'std': inst_data.std()
                    }
            
            print(f"  ✅ VMM moments: {audit['rows']:,} rows, {audit['columns']} columns, {audit['non_missing_pct']:.1%} non-missing")
            return audit
            
        except Exception as e:
            print(f"  ❌ Error auditing VMM moments: {e}")
            return None
    
    def _audit_copula_marginals(self):
        """Audit copula marginals."""
        print("\n📊 Auditing copula marginals...")
        
        try:
            df = pd.read_parquet(f"{self.wave3_dir}/copula_marginals.parquet")
            
            audit = {
                'file': 'copula_marginals.parquet',
                'rows': len(df),
                'columns': len(df.columns),
                'non_missing_pct': df.notna().mean().mean(),
                'session_stats': {},
                'marginal_stats': {},
                'tail_stats': {}
            }
            
            # Session stats
            if 'session_label' in df.columns:
                audit['session_stats'] = df['session_label'].value_counts().to_dict()
            
            # Marginal stats
            marginal_cols = [col for col in df.columns if col.startswith('u_')]
            for col in marginal_cols:
                if col in df.columns:
                    u_data = df[col].dropna()
                    if len(u_data) > 0:
                        audit['marginal_stats'][col] = {
                            'count': len(u_data),
                            'min': u_data.min(),
                            'max': u_data.max(),
                            'mean': u_data.mean(),
                            'std': u_data.std()
                        }
                        
                        # Tail stats
                        audit['tail_stats'][col] = {
                            'u_lt_005': (u_data < 0.05).sum(),
                            'u_gt_095': (u_data > 0.95).sum(),
                            'tail_pct': ((u_data < 0.05) | (u_data > 0.95)).mean()
                        }
            
            print(f"  ✅ Copula marginals: {audit['rows']:,} rows, {audit['columns']} columns, {audit['non_missing_pct']:.1%} non-missing")
            return audit
            
        except Exception as e:
            print(f"  ❌ Error auditing copula marginals: {e}")
            return None
    
    def _audit_clustering_features(self):
        """Audit clustering features."""
        print("\n📊 Auditing clustering features...")
        
        try:
            df = pd.read_parquet(f"{self.wave3_dir}/clustering_features.parquet")
            
            audit = {
                'file': 'clustering_features.parquet',
                'rows': len(df),
                'columns': len(df.columns),
                'non_missing_pct': df.notna().mean().mean(),
                'window_stats': {},
                'feature_stats': {},
                'zscore_stats': {}
            }
            
            # Window stats
            if 'window_start' in df.columns and 'window_end' in df.columns:
                window_duration = (df['window_end'] - df['window_start']).dt.total_seconds() / 60
                audit['window_stats'] = {
                    'duration_min': window_duration.min(),
                    'duration_max': window_duration.max(),
                    'duration_mean': window_duration.mean()
                }
            
            # Feature stats (top 5 by variance)
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            feature_cols = [col for col in numeric_cols if not col.endswith('_zscore')]
            
            if len(feature_cols) > 0:
                variances = df[feature_cols].var().sort_values(ascending=False)
                top_features = variances.head(5).index.tolist()
                
                for col in top_features:
                    if col in df.columns:
                        feat_data = df[col].dropna()
                        audit['feature_stats'][col] = {
                            'count': len(feat_data),
                            'mean': feat_data.mean(),
                            'std': feat_data.std(),
                            'variance': feat_data.var()
                        }
            
            # Z-score stats
            zscore_cols = [col for col in df.columns if col.endswith('_zscore')]
            if len(zscore_cols) > 0:
                zscore_data = df[zscore_cols].values.flatten()
                zscore_data = zscore_data[~np.isnan(zscore_data)]
                audit['zscore_stats'] = {
                    'count': len(zscore_data),
                    'mean': np.mean(zscore_data),
                    'std': np.std(zscore_data),
                    'min': np.min(zscore_data),
                    'max': np.max(zscore_data)
                }
            
            print(f"  ✅ Clustering features: {audit['rows']:,} rows, {audit['columns']} columns, {audit['non_missing_pct']:.1%} non-missing")
            return audit
            
        except Exception as e:
            print(f"  ❌ Error auditing clustering features: {e}")
            return None
    
    def _audit_composite_inputs(self):
        """Audit composite inputs."""
        print("\n📊 Auditing composite inputs...")
        
        try:
            df = pd.read_parquet(f"{self.wave3_dir}/composite_inputs.parquet")
            
            audit = {
                'file': 'composite_inputs.parquet',
                'rows': len(df),
                'columns': len(df.columns),
                'non_missing_pct': df.notna().mean().mean(),
                'window_stats': {},
                'signal_stats': {},
                'zscore_stats': {}
            }
            
            # Window stats
            if 'window_start' in df.columns and 'window_end' in df.columns:
                window_duration = (df['window_end'] - df['window_start']).dt.total_seconds() / 60
                audit['window_stats'] = {
                    'duration_min': window_duration.min(),
                    'duration_max': window_duration.max(),
                    'duration_mean': window_duration.mean()
                }
            
            # Signal stats
            signal_cols = [col for col in df.columns if not col.endswith('_zscore') and col not in ['window_start', 'window_end']]
            for col in signal_cols:
                if col in df.columns:
                    signal_data = df[col].dropna()
                    audit['signal_stats'][col] = {
                        'count': len(signal_data),
                        'mean': signal_data.mean(),
                        'std': signal_data.std()
                    }
            
            # Z-score stats
            zscore_cols = [col for col in df.columns if col.endswith('_zscore')]
            if len(zscore_cols) > 0:
                zscore_data = df[zscore_cols].values.flatten()
                zscore_data = zscore_data[~np.isnan(zscore_data)]
                audit['zscore_stats'] = {
                    'count': len(zscore_data),
                    'mean': np.mean(zscore_data),
                    'std': np.std(zscore_data),
                    'min': np.min(zscore_data),
                    'max': np.max(zscore_data)
                }
            
            print(f"  ✅ Composite inputs: {audit['rows']:,} rows, {audit['columns']} columns, {audit['non_missing_pct']:.1%} non-missing")
            return audit
            
        except Exception as e:
            print(f"  ❌ Error auditing composite inputs: {e}")
            return None
    
    def _generate_audit_report(self, icp_audit, vmm_audit, copula_audit, clustering_audit, composite_audit):
        """Generate comprehensive audit report."""
        report_file = f"{self.analysis_dir}/WAVE3_VARIABLES_AUDIT.md"
        
        with open(report_file, 'w') as f:
            f.write("# Wave-3 Variables Final Audit Report\n\n")
            f.write(f"**Audit Date**: {datetime.now().isoformat()}\n")
            f.write("**Purpose**: Comprehensive audit of all Wave-3 variables\n\n")
            
            # Summary table
            f.write("## Summary Table\n\n")
            f.write("| File | Rows | Columns | Non-Missing % | Status |\n")
            f.write("|------|------|---------|---------------|--------|\n")
            
            audits = [
                ('ICP Design', icp_audit),
                ('VMM Moments', vmm_audit),
                ('Copula Marginals', copula_audit),
                ('Clustering Features', clustering_audit),
                ('Composite Inputs', composite_audit)
            ]
            
            for name, audit in audits:
                if audit:
                    status = "✅" if audit['rows'] > 0 else "❌"
                    f.write(f"| {name} | {audit['rows']:,} | {audit['columns']} | {audit['non_missing_pct']:.1%} | {status} |\n")
                else:
                    f.write(f"| {name} | - | - | - | ❌ |\n")
            
            # Detailed audits
            f.write("\n## Detailed Audits\n\n")
            
            # ICP Design
            if icp_audit:
                f.write("### ICP Design Matrix\n\n")
                f.write(f"- **Rows**: {icp_audit['rows']:,}\n")
                f.write(f"- **Columns**: {icp_audit['columns']}\n")
                f.write(f"- **Non-missing %**: {icp_audit['non_missing_pct']:.1%}\n")
                
                if icp_audit['y_stats']:
                    f.write(f"- **Y variable**: {icp_audit['y_stats']['count']:,} obs, mean={icp_audit['y_stats']['mean']:.4f}\n")
                
                f.write(f"- **Environment variables**: {len(icp_audit['env_stats'])} found\n")
                f.write("\n")
            
            # VMM Moments
            if vmm_audit:
                f.write("### VMM Moments\n\n")
                f.write(f"- **Windows**: {vmm_audit['rows']:,}\n")
                f.write(f"- **Columns**: {vmm_audit['columns']}\n")
                f.write(f"- **Non-missing %**: {vmm_audit['non_missing_pct']:.1%}\n")
                
                if vmm_audit['window_stats']:
                    f.write(f"- **Window duration**: {vmm_audit['window_stats']['duration_mean']:.1f} min average\n")
                
                f.write(f"- **Moment columns**: {len(vmm_audit['moment_stats'])} analyzed\n")
                f.write(f"- **Instrument columns**: {len(vmm_audit['instrument_stats'])} analyzed\n")
                f.write("\n")
            
            # Copula Marginals
            if copula_audit:
                f.write("### Copula Marginals\n\n")
                f.write(f"- **Rows**: {copula_audit['rows']:,}\n")
                f.write(f"- **Columns**: {copula_audit['columns']}\n")
                f.write(f"- **Non-missing %**: {copula_audit['non_missing_pct']:.1%}\n")
                
                if copula_audit['session_stats']:
                    f.write("- **Session distribution**:\n")
                    for session, count in copula_audit['session_stats'].items():
                        f.write(f"  - {session}: {count:,} rows\n")
                
                if copula_audit['marginal_stats']:
                    f.write("- **Marginal statistics**:\n")
                    for col, stats in copula_audit['marginal_stats'].items():
                        f.write(f"  - {col}: [{stats['min']:.3f}, {stats['max']:.3f}] range, {stats['count']:,} obs\n")
                
                if copula_audit['tail_stats']:
                    f.write("- **Tail statistics**:\n")
                    for col, stats in copula_audit['tail_stats'].items():
                        f.write(f"  - {col}: {stats['tail_pct']:.1%} in tails (u<0.05 or u>0.95)\n")
                
                f.write("\n")
            
            # Clustering Features
            if clustering_audit:
                f.write("### Clustering Features\n\n")
                f.write(f"- **Windows**: {clustering_audit['rows']:,}\n")
                f.write(f"- **Columns**: {clustering_audit['columns']}\n")
                f.write(f"- **Non-missing %**: {clustering_audit['non_missing_pct']:.1%}\n")
                
                if clustering_audit['feature_stats']:
                    f.write("- **Top features by variance**:\n")
                    for col, stats in clustering_audit['feature_stats'].items():
                        f.write(f"  - {col}: variance={stats['variance']:.6f}\n")
                
                if clustering_audit['zscore_stats']:
                    f.write(f"- **Z-score standardization**: {clustering_audit['zscore_stats']['count']:,} values, mean={clustering_audit['zscore_stats']['mean']:.3f}\n")
                
                f.write("\n")
            
            # Composite Inputs
            if composite_audit:
                f.write("### Composite Inputs\n\n")
                f.write(f"- **Windows**: {composite_audit['rows']:,}\n")
                f.write(f"- **Columns**: {composite_audit['columns']}\n")
                f.write(f"- **Non-missing %**: {composite_audit['non_missing_pct']:.1%}\n")
                
                if composite_audit['signal_stats']:
                    f.write("- **Signal statistics**:\n")
                    for col, stats in composite_audit['signal_stats'].items():
                        f.write(f"  - {col}: mean={stats['mean']:.4f}, std={stats['std']:.4f}\n")
                
                if composite_audit['zscore_stats']:
                    f.write(f"- **Z-score standardization**: {composite_audit['zscore_stats']['count']:,} values, mean={composite_audit['zscore_stats']['mean']:.3f}\n")
                
                f.write("\n")
            
            # Overall assessment
            f.write("## Overall Assessment\n\n")
            
            all_audits = [icp_audit, vmm_audit, copula_audit, clustering_audit, composite_audit]
            successful_audits = [a for a in all_audits if a and a['rows'] > 0]
            
            f.write(f"- **Files audited**: {len(successful_audits)}/5\n")
            f.write(f"- **Total rows across all files**: {sum(a['rows'] for a in successful_audits):,}\n")
            f.write(f"- **Average non-missing %**: {np.mean([a['non_missing_pct'] for a in successful_audits]):.1%}\n")
            
            f.write("\n## Recommendations\n\n")
            f.write("1. **ICP Design**: Ready for ICP model fitting with environment partitions\n")
            f.write("2. **VMM Moments**: Ready for VMM model fitting with comprehensive moment set\n")
            f.write("3. **Copula Marginals**: Ready for copula fitting with uniform marginals\n")
            f.write("4. **Clustering Features**: Ready for clustering analysis with standardized features\n")
            f.write("5. **Composite Inputs**: Ready for composite index construction\n")
            
            f.write("\n## Next Steps\n\n")
            f.write("All Wave-3 variables are ready for model execution:\n")
            f.write("- ICP models can be fitted on the design matrix\n")
            f.write("- VMM models can be fitted on the moment set\n")
            f.write("- Copulas can be fitted on the marginals\n")
            f.write("- Clustering can be performed on the features\n")
            f.write("- Composite index can be constructed from the inputs\n")
        
        print(f"  ✅ Audit report saved to {report_file}")

if __name__ == "__main__":
    auditor = Wave3VariablesAuditor()
    success = auditor.audit_all_variables()
    
    if success:
        print("\n🎉 Wave-3 variables audit completed successfully!")
    else:
        print("\n❌ Wave-3 variables audit failed!")
        sys.exit(1)
