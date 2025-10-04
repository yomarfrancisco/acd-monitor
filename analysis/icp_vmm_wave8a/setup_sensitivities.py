#!/usr/bin/env python3
"""
Wave 8a - Setup Sensitivities
Load Wave 6/7/8 data and prepare for "What-If" sensitivity tests
"""

import os
import pandas as pd
import json
import numpy as np
from datetime import datetime
import hashlib

def setup_sensitivities():
    """Setup data and parameters for Wave 8a sensitivity tests"""
    print("Wave 8a - Setup Sensitivities")
    print("=" * 50)
    
    # Set random seed
    np.random.seed(1729)
    print(f"🌱 Random seed set: 1729")
    
    # Load Wave 7 design matrix
    design_path = "analysis/icp_vmm_wave7/design/design_matrix_v1.parquet"
    if not os.path.exists(design_path):
        print("❌ Wave 7 design matrix not found!")
        return None
    
    df = pd.read_parquet(design_path)
    df.index = pd.to_datetime(df.index)
    
    print(f"📊 Design matrix loaded: {len(df):,} rows")
    print(f"⏱️  Time span: {(df.index.max() - df.index.min()).total_seconds()/3600:.1f} hours")
    
    # Load Wave 7 derived data
    derived_path = "analysis/icp_vmm_wave7/derived_data_v1.parquet"
    if not os.path.exists(derived_path):
        print("❌ Wave 7 derived data not found!")
        return None
    
    derived_df = pd.read_parquet(derived_path)
    derived_df.index = pd.to_datetime(derived_df.index)
    
    print(f"📊 Derived data loaded: {len(derived_df):,} rows")
    
    # Load Wave 8 baseline config
    config_path = "analysis/icp_vmm_wave8/baseline_config_v1.json"
    if not os.path.exists(config_path):
        print("❌ Wave 8 baseline config not found!")
        return None
    
    with open(config_path, 'r') as f:
        wave8_config = json.load(f)
    
    print(f"📊 Wave 8 config loaded")
    
    # Check for Wave 6 wash screens
    wash_path = "analysis/wash_screens_v2"
    wash_available = os.path.exists(wash_path)
    print(f"📊 Wash screens available: {wash_available}")
    
    # Define venues for sensitivity tests
    all_venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    no_bitget_venues = ['BINANCE', 'COINBASE', 'BYBITSPOT']
    
    # Create sensitivity configuration
    sensitivity_config = {
        'setup_timestamp': datetime.now().isoformat(),
        'random_seed': 1729,
        'data_sources': {
            'design_matrix': design_path,
            'derived_data': derived_path,
            'wave8_config': config_path,
            'wash_screens': wash_path if wash_available else None
        },
        'venues': {
            'all_venues': all_venues,
            'no_bitget_venues': no_bitget_venues
        },
        'total_observations': len(df),
        'time_span_hours': (df.index.max() - df.index.min()).total_seconds() / 3600,
        'commit_sha': get_commit_sha(),
        'data_hash': get_data_hash(df),
        'wash_available': wash_available
    }
    
    # Save sensitivity configuration
    os.makedirs('analysis/icp_vmm_wave8a', exist_ok=True)
    
    with open('analysis/icp_vmm_wave8a/sensitivity_config_v1.json', 'w') as f:
        json.dump(sensitivity_config, f, indent=2, default=str)
    
    # Create heartbeat
    heartbeat = {
        'timestamp': datetime.now().isoformat(),
        'status': 'SETUP_COMPLETE',
        'total_observations': len(df),
        'venues': all_venues,
        'no_bitget_venues': no_bitget_venues,
        'wash_available': wash_available
    }
    
    os.makedirs('analysis/_diag', exist_ok=True)
    with open('analysis/_diag/icp_wave8a_heartbeat.json', 'w') as f:
        json.dump(heartbeat, f, indent=2)
    
    print(f"\n✅ Sensitivity setup completed")
    print(f"📄 Config: analysis/icp_vmm_wave8a/sensitivity_config_v1.json")
    print(f"📄 Heartbeat: analysis/_diag/icp_wave8a_heartbeat.json")
    
    return df, derived_df, wave8_config, wash_available

def get_commit_sha():
    """Get current commit SHA"""
    try:
        import subprocess
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except:
        return "unknown"

def get_data_hash(df):
    """Get hash of data for provenance tracking"""
    try:
        data_str = f"{len(df)}_{df.index.min()}_{df.index.max()}_{list(df.columns)}"
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
    except:
        return "unknown"

if __name__ == "__main__":
    result = setup_sensitivities()
    
    if result is not None:
        print(f"\n✅ Sensitivity setup completed - proceeding to No-Bitget test")
    else:
        print(f"\n❌ Sensitivity setup failed - stopping execution")
