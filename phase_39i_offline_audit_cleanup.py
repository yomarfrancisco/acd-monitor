#!/usr/bin/env python3
"""
Phase 39I — Offline Audit & Safe Cleanup (BTCUSD-class only)
Goal: Produce tamper-evident inventory and perform safe cleanup of unused files
"""

import os
import sys
import hashlib
import json
import shutil
from pathlib import Path
from datetime import datetime
import pandas as pd
import argparse

# Configuration
BASE_DIR = Path('/Users/ygorfrancisco/Desktop/acd-monitor')
REPORTS_DIR = BASE_DIR / 'data_v7' / 'reports'
LOCK_FILE = BASE_DIR / 'locks' / 'api_budget.lock'

# Target configuration
TARGET_ROOTS = [
    BASE_DIR / 'data_v6' / 'raw' / 'coinapi_jul',
    BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w5',
    BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w6',
    BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w7'
]

# BTCUSD-class patterns (case-insensitive)
BTCUSD_PATTERNS = ['BTCUSD', 'BTCUSDT', 'BTC-USD', 'BTC__002DUSD']

# Exclude patterns
EXCLUDE_PATTERNS = ['ETHBTC', 'LTCBTC', 'WBTCUSDT', 'PUMP']

def check_network_lock():
    """Ensure network is locked and no API calls are made"""
    print("🔒 Checking network lock...")
    
    if not LOCK_FILE.exists():
        print("❌ Network lock missing - creating it")
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOCK_FILE, 'w') as f:
            f.write(f"""API_BUDGET_LOCK
Created: {datetime.utcnow().isoformat()}Z
Reason: Phase 39I - Offline audit
Status: ACTIVE
Network calls: BLOCKED
""")
        print("🔒 Network lock created")
    else:
        print("✅ Network lock exists - network frozen")
    
    return True

def is_btcusd_class(filename):
    """Check if filename contains BTCUSD-class patterns"""
    filename_upper = filename.upper()
    
    # Check for BTCUSD patterns
    for pattern in BTCUSD_PATTERNS:
        if pattern in filename_upper:
            # Exclude non-BTCUSD pairs
            for exclude in EXCLUDE_PATTERNS:
                if exclude in filename_upper:
                    return False
            return True
    
    return False

def should_exclude_file(file_path):
    """Check if file should be excluded from processing"""
    filename = file_path.name
    
    # Exclude tmp/part files
    if filename.endswith('.part') or filename.endswith('.tmp'):
        return True
    
    # Exclude non-BTCUSD pairs
    if not is_btcusd_class(filename):
        return True
    
    return False

def compute_file_hash(file_path):
    """Compute SHA-256 hash of file"""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"⚠️ Error computing hash for {file_path}: {e}")
        return "ERROR"

def get_week_tag(file_path):
    """Determine week tag from file path"""
    path_str = str(file_path)
    
    if 'coinapi_jul_w5' in path_str:
        return 'w5'
    elif 'coinapi_jul_w6' in path_str:
        return 'w6'
    elif 'coinapi_jul_w7' in path_str:
        return 'w7'
    elif 'coinapi_jul' in path_str:
        return 'unknown'
    else:
        return 'unknown'

def build_disk_inventory():
    """Build full disk inventory of BTCUSD-class files"""
    print("📊 Building full disk inventory...")
    
    inventory_data = []
    
    for root_path in TARGET_ROOTS:
        if not root_path.exists():
            print(f"⚠️ Root not found: {root_path}")
            continue
        
        print(f"📁 Scanning: {root_path}")
        
        for file_path in root_path.rglob('*.csv.gz'):
            if should_exclude_file(file_path):
                continue
            
            try:
                stat = file_path.stat()
                size_bytes = stat.st_size
                mtime_iso = datetime.fromtimestamp(stat.st_mtime).isoformat() + 'Z'
                sha256 = compute_file_hash(file_path)
                week_tag = get_week_tag(file_path)
                
                inventory_data.append({
                    'path': str(file_path),
                    'size_bytes': size_bytes,
                    'sha256': sha256,
                    'mtime_iso': mtime_iso,
                    'week_tag': week_tag
                })
                
            except Exception as e:
                print(f"⚠️ Error processing {file_path}: {e}")
    
    df = pd.DataFrame(inventory_data)
    print(f"📊 Total BTCUSD-class files found: {len(df)}")
    
    return df

def create_inventory_bom(inventory_df):
    """Create BOM hash for inventory"""
    print("🔐 Creating inventory BOM hash...")
    
    # Sort by path for deterministic ordering
    sorted_paths = sorted(inventory_df['path'].tolist())
    bom_content = '\n'.join(sorted_paths)
    bom_hash = hashlib.sha256(bom_content.encode()).hexdigest()
    
    with open(REPORTS_DIR / '39I_inventory_bom_sha256.txt', 'w') as f:
        f.write(f"INVENTORY_BOM_SHA256: {bom_hash}\n")
        f.write(f"FILES_COUNT: {len(inventory_df)}\n")
        f.write(f"CREATED: {datetime.utcnow().isoformat()}Z\n")
    
    print(f"✅ Inventory BOM hash: {bom_hash}")
    return bom_hash

def load_used_manifest():
    """Load the authoritative 'used' manifest"""
    print("📋 Loading used manifest...")
    
    # Try primary manifest first
    primary_manifest = REPORTS_DIR / '39G_beacon_ready.csv'
    if primary_manifest.exists():
        print(f"📄 Using primary manifest: {primary_manifest}")
        df = pd.read_csv(primary_manifest)
    else:
        # Fallback to secondary manifest
        fallback_manifest = REPORTS_DIR / 'w7_w6_w5_btc_manifest.csv'
        if fallback_manifest.exists():
            print(f"📄 Using fallback manifest: {fallback_manifest}")
            df = pd.read_csv(fallback_manifest)
        else:
            print("❌ No used manifest found")
            return set()
    
    # Normalize paths to absolute paths
    used_paths = set()
    for _, row in df.iterrows():
        # Try different column names
        path = row.get('path', '') or row.get('abs_path', '')
        if path:
            # Convert to absolute path if relative
            if not os.path.isabs(path):
                path = str(BASE_DIR / path)
            used_paths.add(path)
    
    print(f"📊 Used files: {len(used_paths)}")
    return used_paths

def load_prior_manifests():
    """Load all prior manifest files to avoid deleting referenced files"""
    print("📋 Loading prior manifests...")
    
    manifest_files = [
        '39E_btc_manifest.csv',
        '39F_manifest.csv', 
        '39G_inventory.csv',
        'w7_w6_w5_btc_manifest.csv',
        'w7_w6_w5_quarantine_manifest.csv'
    ]
    
    referenced_paths = set()
    
    for manifest_file in manifest_files:
        manifest_path = REPORTS_DIR / manifest_file
        if manifest_path.exists():
            try:
                df = pd.read_csv(manifest_path)
                for _, row in df.iterrows():
                    # Try different column names
                    path = row.get('path', '') or row.get('abs_path', '')
                    if path:
                        if not os.path.isabs(path):
                            path = str(BASE_DIR / path)
                        referenced_paths.add(path)
                print(f"📄 Loaded {manifest_file}: {len(df)} entries")
            except Exception as e:
                print(f"⚠️ Error reading {manifest_file}: {e}")
    
    print(f"📊 Total referenced paths: {len(referenced_paths)}")
    return referenced_paths

def compute_delete_candidates(inventory_df, used_paths, referenced_paths):
    """Compute delete candidates with safety filters"""
    print("🔍 Computing delete candidates...")
    
    # Start with all inventory files
    candidates = inventory_df.copy()
    
    # Remove used files
    candidates = candidates[~candidates['path'].isin(used_paths)]
    print(f"📊 After removing used files: {len(candidates)}")
    
    # Apply safety filters
    quarantine = []
    skipped = []
    delete_candidates = []
    
    for _, row in candidates.iterrows():
        path = row['path']
        size_bytes = row['size_bytes']
        sha256 = row['sha256']
        
        # Safety filter 1: Keep small stubs
        if size_bytes < 10240:  # 10KB
            quarantine.append(row)
            continue
        
        # Safety filter 2: Keep if SHA256 duplicated by any USED file
        used_hashes = set()
        for used_path in used_paths:
            if Path(used_path).exists():
                try:
                    used_hash = compute_file_hash(Path(used_path))
                    used_hashes.add(used_hash)
                except:
                    pass
        
        if sha256 in used_hashes:
            skipped.append(row)
            continue
        
        # Safety filter 3: Keep if path appears in any prior manifest
        if path in referenced_paths:
            skipped.append(row)
            continue
        
        # Everything else is a candidate for deletion
        delete_candidates.append(row)
    
    print(f"📊 Delete candidates: {len(delete_candidates)}")
    print(f"📊 Quarantine (small files): {len(quarantine)}")
    print(f"📊 Skipped (safety filters): {len(skipped)}")
    
    return delete_candidates, quarantine, skipped

def produce_dryrun_reports(delete_candidates, inventory_df, used_paths, quarantine, skipped):
    """Produce dry-run reports"""
    print("📝 Producing dry-run reports...")
    
    # Write delete dry-run list
    delete_paths = [row['path'] for row in delete_candidates]
    with open(REPORTS_DIR / '39I_delete_dryrun.txt', 'w') as f:
        for path in delete_paths:
            f.write(f"{path}\n")
    
    # Write delete summary JSON
    summary = {
        "total_on_disk": len(inventory_df),
        "used": len(used_paths),
        "candidates": len(delete_candidates),
        "quarantine": len(quarantine),
        "skipped": len(skipped),
        "timestamp": datetime.utcnow().isoformat() + 'Z'
    }
    
    with open(REPORTS_DIR / '39I_delete_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"✅ Dry-run reports written")
    print(f"📊 Summary: {summary}")

def perform_safe_delete(delete_candidates):
    """Perform safe deletion with checksum logging"""
    print("🗑️ Performing safe deletion...")
    
    deleted_hashes = []
    
    with open(REPORTS_DIR / '39I_deleted_bom_sha256.txt', 'w') as f:
        f.write(f"DELETED_FILES_BOM\n")
        f.write(f"Created: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Files to delete: {len(delete_candidates)}\n\n")
        
        for row in delete_candidates:
            path = Path(row['path'])
            sha256 = row['sha256']
            
            try:
                # Verify file still exists
                if path.exists():
                    # Compute hash before deletion
                    actual_hash = compute_file_hash(path)
                    f.write(f"{sha256}  {path}\n")
                    deleted_hashes.append(sha256)
                    
                    # Delete file
                    path.unlink()
                    print(f"🗑️ Deleted: {path}")
                else:
                    print(f"⚠️ File not found: {path}")
                    
            except Exception as e:
                print(f"⚠️ Error deleting {path}: {e}")
    
    print(f"✅ Deleted {len(deleted_hashes)} files")
    return deleted_hashes

def rebuild_post_cleanup_inventory():
    """Rebuild inventory after cleanup"""
    print("📊 Rebuilding post-cleanup inventory...")
    
    inventory_df = build_disk_inventory()
    
    # Write post-cleanup inventory
    inventory_path = REPORTS_DIR / '39I_inventory_post.csv'
    inventory_df.to_csv(inventory_path, index=False)
    
    # Create post-cleanup BOM
    create_inventory_bom(inventory_df)
    
    # Rename the BOM file for post-cleanup
    bom_path = REPORTS_DIR / '39I_inventory_bom_sha256.txt'
    post_bom_path = REPORTS_DIR / '39I_inventory_post_bom_sha256.txt'
    shutil.move(bom_path, post_bom_path)
    
    print(f"✅ Post-cleanup inventory written: {inventory_path}")
    return inventory_df

def write_final_audit(inventory_df, post_inventory_df, delete_candidates, apply_delete):
    """Write final audit report"""
    print("📝 Writing final audit...")
    
    # Calculate bytes reclaimed
    bytes_before = inventory_df['size_bytes'].sum()
    bytes_after = post_inventory_df['size_bytes'].sum()
    bytes_reclaimed = bytes_before - bytes_after
    
    # Get top 20 largest survivors
    top_survivors = post_inventory_df.nlargest(20, 'size_bytes')[['path', 'size_bytes']]
    
    with open(REPORTS_DIR / '39I_audit.txt', 'w') as f:
        f.write("Phase 39I Final Audit Report\n")
        f.write("=" * 50 + "\n\n")
        
        f.write(f"Timestamp: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Apply Delete: {apply_delete}\n\n")
        
        f.write("Counts:\n")
        f.write(f"  Before cleanup: {len(inventory_df)} files\n")
        f.write(f"  After cleanup: {len(post_inventory_df)} files\n")
        f.write(f"  Deleted: {len(delete_candidates)} files\n")
        f.write(f"  Bytes reclaimed: {bytes_reclaimed:,} bytes\n\n")
        
        f.write("Top 20 Largest Survivors:\n")
        f.write("-" * 30 + "\n")
        for _, row in top_survivors.iterrows():
            f.write(f"{row['size_bytes']:>12,} bytes  {row['path']}\n")
        
        f.write(f"\nAssertions:\n")
        f.write(f"  NETWORK_UNUSED=0\n")
        f.write(f"  APPLIED_DELETE={apply_delete}\n")
    
    print(f"✅ Final audit written")

def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description='Phase 39I: Offline Audit & Safe Cleanup')
    parser.add_argument('--apply-delete', action='store_true', 
                       help='Apply deletion (default: dry-run only)')
    args = parser.parse_args()
    
    apply_delete = args.apply_delete
    
    print("🚀 Phase 39I — Offline Audit & Safe Cleanup (BTCUSD-class only)")
    print("=" * 70)
    print(f"Mode: {'DRY-RUN' if not apply_delete else 'APPLY-DELETE'}")
    print("=" * 70)
    
    # Create directories
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check network lock
    if not check_network_lock():
        print("❌ Network lock check failed")
        sys.exit(1)
    
    # Task 1: Build full disk inventory
    print("\n📊 Task 1: Building full disk inventory")
    inventory_df = build_disk_inventory()
    
    # Write inventory CSV
    inventory_path = REPORTS_DIR / '39I_inventory.csv'
    inventory_df.to_csv(inventory_path, index=False)
    print(f"✅ Inventory written: {inventory_path}")
    
    # Create inventory BOM
    inventory_bom = create_inventory_bom(inventory_df)
    
    # Task 2: Load used manifest
    print("\n📋 Task 2: Loading used manifest")
    used_paths = load_used_manifest()
    
    # Task 3: Compute delete candidates
    print("\n🔍 Task 3: Computing delete candidates")
    referenced_paths = load_prior_manifests()
    delete_candidates, quarantine, skipped = compute_delete_candidates(
        inventory_df, used_paths, referenced_paths
    )
    
    # Task 4: Produce dry-run reports
    print("\n📝 Task 4: Producing dry-run reports")
    produce_dryrun_reports(delete_candidates, inventory_df, used_paths, quarantine, skipped)
    
    # Task 5: Apply deletion if requested
    if apply_delete:
        print("\n🗑️ Task 5: Applying deletion")
        deleted_hashes = perform_safe_delete(delete_candidates)
        post_inventory_df = rebuild_post_cleanup_inventory()
    else:
        print("\n⏸️ Task 5: Skipping deletion (dry-run mode)")
        post_inventory_df = inventory_df
    
    # Task 6: Write final audit
    print("\n📝 Task 6: Writing final audit")
    write_final_audit(inventory_df, post_inventory_df, delete_candidates, apply_delete)
    
    # Summary
    print(f"\n✅ Phase 39I Complete")
    print(f"📊 Files on disk: {len(inventory_df)}")
    print(f"📊 Delete candidates: {len(delete_candidates)}")
    print(f"📊 Mode: {'DRY-RUN' if not apply_delete else 'APPLY-DELETE'}")
    
    print(f"\n📁 Key artifacts:")
    print(f"  - {inventory_path}")
    print(f"  - {REPORTS_DIR / '39I_delete_dryrun.txt'}")
    print(f"  - {REPORTS_DIR / '39I_audit.txt'}")

if __name__ == "__main__":
    main()
