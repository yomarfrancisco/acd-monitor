#!/usr/bin/env python3
"""
Wave 8 - Setup Baseline
Load Wave 6/7 data and prepare for robustness testing
"""

import os
import pandas as pd
import json
import numpy as np
from datetime import datetime
import hashlib

def setup_baseline():
    """Setup baseline data and parameters for Wave 8 robustness testing"""
    print("Wave 8 - Setup Baseline")
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
    
    # Load Wave 7 final edges
    graph_path = "analysis/icp_vmm_wave7/graph/graph_v1.json"
    if not os.path.exists(graph_path):
        print("❌ Wave 7 final edges not found!")
        return None
    
    with open(graph_path, 'r') as f:
        wave7_results = json.load(f)
    
    wave7_edges = wave7_results['edges']
    print(f"📊 Wave 7 edges: {len(wave7_edges)}")
    
    # Define parameters
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    lags = [1, 2, 3, 5, 10]  # seconds
    scales = [1, 5, 30]  # seconds
    
    # Create baseline configuration
    baseline_config = {
        'setup_timestamp': datetime.now().isoformat(),
        'random_seed': 1729,
        'data_source': design_path,
        'wave7_edges_count': len(wave7_edges),
        'venues': venues,
        'lags': lags,
        'scales': scales,
        'total_observations': len(df),
        'time_span_hours': (df.index.max() - df.index.min()).total_seconds() / 3600,
        'commit_sha': get_commit_sha(),
        'data_hash': get_data_hash(df)
    }
    
    # Save baseline configuration
    os.makedirs('analysis/icp_vmm_wave8', exist_ok=True)
    
    with open('analysis/icp_vmm_wave8/baseline_config_v1.json', 'w') as f:
        json.dump(baseline_config, f, indent=2, default=str)
    
    # Create heartbeat
    heartbeat = {
        'timestamp': datetime.now().isoformat(),
        'status': 'SETUP_COMPLETE',
        'total_observations': len(df),
        'wave7_edges': len(wave7_edges),
        'venues': venues,
        'scales': scales
    }
    
    os.makedirs('analysis/_diag', exist_ok=True)
    with open('analysis/_diag/wave8_heartbeat.json', 'w') as f:
        json.dump(heartbeat, f, indent=2)
    
    print(f"\n✅ Baseline setup completed")
    print(f"📄 Config: analysis/icp_vmm_wave8/baseline_config_v1.json")
    print(f"📄 Heartbeat: analysis/_diag/wave8_heartbeat.json")
    
    return df, wave7_edges, baseline_config

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
        # Create a hash of the data structure
        data_str = f"{len(df)}_{df.index.min()}_{df.index.max()}_{list(df.columns)}"
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
    except:
        return "unknown"

if __name__ == "__main__":
    result = setup_baseline()
    
    if result is not None:
        print(f"\n✅ Baseline setup completed - proceeding to robustness grid")
    else:
        print(f"\n❌ Baseline setup failed - stopping execution")
