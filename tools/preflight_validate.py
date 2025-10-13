#!/usr/bin/env python3
"""
Preflight Validator - Phase 39J
Validates download configuration before making API calls
"""

import os
import sys
import hashlib
import yaml
from pathlib import Path

# Configuration
BASE_DIR = Path('/Users/ygorfrancisco/Desktop/acd-monitor')
LOCK_FILE = BASE_DIR / 'locks' / 'api_budget.lock'
DOWNLOAD_METHOD_FILE = BASE_DIR / 'data_v7' / 'reports' / 'DOWNLOAD_METHOD.md'
DOWNLOAD_METHOD_SHA = BASE_DIR / 'data_v7' / 'reports' / 'DOWNLOAD_METHOD.sha256'
PIPELINE_LOCK_FILE = BASE_DIR / 'PIPELINE_LOCK.yaml'
PIPELINE_LOCK_SHA = BASE_DIR / 'PIPELINE_LOCK.sha256'

def compute_file_hash(file_path):
    """Compute SHA-256 hash of file"""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"Error computing hash for {file_path}: {e}")
        return None

def verify_api_budget_lock():
    """Verify API budget lock exists or create it"""
    if not LOCK_FILE.exists():
        print("Creating API budget lock...")
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOCK_FILE, 'w') as f:
            f.write("API_BUDGET_LOCK\nStatus: ACTIVE\nNetwork calls: BLOCKED\n")
        print("✅ API budget lock created")
    else:
        print("✅ API budget lock exists")
    return True

def verify_download_method():
    """Verify DOWNLOAD_METHOD.md and its SHA"""
    if not DOWNLOAD_METHOD_FILE.exists():
        print("❌ DOWNLOAD_METHOD.md not found")
        return False
    
    if not DOWNLOAD_METHOD_SHA.exists():
        print("❌ DOWNLOAD_METHOD.sha256 not found")
        return False
    
    # Compute current hash
    current_hash = compute_file_hash(DOWNLOAD_METHOD_FILE)
    if not current_hash:
        print("❌ Error computing DOWNLOAD_METHOD.md hash")
        return False
    
    # Read expected hash
    with open(DOWNLOAD_METHOD_SHA, 'r') as f:
        expected_hash = f.read().strip()
    
    if current_hash != expected_hash:
        print(f"❌ DOWNLOAD_METHOD.md hash mismatch")
        print(f"  Expected: {expected_hash}")
        print(f"  Current:  {current_hash}")
        return False
    
    print("✅ DOWNLOAD_METHOD.md verified")
    return True

def verify_pipeline_lock():
    """Verify PIPELINE_LOCK.yaml and its SHA"""
    if not PIPELINE_LOCK_FILE.exists():
        print("❌ PIPELINE_LOCK.yaml not found")
        return False
    
    if not PIPELINE_LOCK_SHA.exists():
        print("❌ PIPELINE_LOCK.sha256 not found")
        return False
    
    # Compute current hash
    current_hash = compute_file_hash(PIPELINE_LOCK_FILE)
    if not current_hash:
        print("❌ Error computing PIPELINE_LOCK.yaml hash")
        return False
    
    # Read expected hash
    with open(PIPELINE_LOCK_SHA, 'r') as f:
        expected_hash = f.read().strip()
    
    if current_hash != expected_hash:
        print(f"❌ PIPELINE_LOCK.yaml hash mismatch")
        print(f"  Expected: {expected_hash}")
        print(f"  Current:  {current_hash}")
        return False
    
    print("✅ PIPELINE_LOCK.yaml verified")
    return True

def verify_downloader_script():
    """Verify downloader script hash matches pipeline lock"""
    # Get the script path from command line or use default
    script_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    if not script_path:
        print("❌ No downloader script specified")
        return False
    
    script_path = Path(script_path)
    if not script_path.exists():
        print(f"❌ Downloader script not found: {script_path}")
        return False
    
    # Compute script hash
    script_hash = compute_file_hash(script_path)
    if not script_hash:
        print("❌ Error computing script hash")
        return False
    
    # Read expected hash from pipeline lock
    try:
        with open(PIPELINE_LOCK_FILE, 'r') as f:
            pipeline_data = yaml.safe_load(f)
        
        expected_hash = pipeline_data.get('download_method_sha', '')
        if not expected_hash:
            print("❌ No download_method_sha in pipeline lock")
            return False
        
        if script_hash != expected_hash:
            print(f"❌ Script hash mismatch")
            print(f"  Expected: {expected_hash}")
            print(f"  Current:  {script_hash}")
            return False
        
        print("✅ Downloader script verified")
        return True
        
    except Exception as e:
        print(f"❌ Error reading pipeline lock: {e}")
        return False

def main():
    """Main validation"""
    print("🔍 Preflight Validation")
    print("=" * 30)
    
    # Run all validations
    checks = [
        verify_api_budget_lock(),
        verify_download_method(),
        verify_pipeline_lock(),
        verify_downloader_script()
    ]
    
    if all(checks):
        print("\n✅ PRELIGHT_OK")
        sys.exit(0)
    else:
        print("\n❌ Preflight validation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
