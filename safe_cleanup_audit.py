#!/usr/bin/env python3
"""
Safe Disk Cleanup Audit - Read-only operations only
Memory limit: ≤250 MB, Runtime: ≤3 minutes
"""

import os
import json
import time
from datetime import datetime, timedelta
import psutil

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024

def get_directory_size(path):
    """Get total size of directory in MB"""
    total_size = 0
    file_count = 0
    
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                    file_count += 1
                except (OSError, FileNotFoundError):
                    continue
    except (OSError, FileNotFoundError):
        pass
    
    return total_size / (1024 * 1024), file_count  # Convert to MB

def get_last_modified(path):
    """Get last modified date of directory"""
    try:
        # Get the most recent modification time of any file in the directory
        latest_time = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    mtime = os.path.getmtime(filepath)
                    latest_time = max(latest_time, mtime)
                except (OSError, FileNotFoundError):
                    continue
        
        if latest_time > 0:
            return datetime.fromtimestamp(latest_time).isoformat()
        else:
            return "unknown"
    except (OSError, FileNotFoundError):
        return "unknown"

def audit_cache_directories():
    """Audit data_v6/cache/ for unused week folders"""
    print("🔍 AUDITING data_v6/cache/ FOR UNUSED WEEK FOLDERS")
    print("=" * 60)
    
    # Active directories that should be kept
    active_directories = {
        'data_v6/cache/beacons/aug_w-4',
        'data_v6/cache/beacons/aug_w-3', 
        'data_v6/cache/beacons/aug_w-2',
        'data_v6/cache/beacons/aug_w-1',
        'data_v6/cache/ticks/aug_w-4',
        'data_v6/cache/ticks/aug_w-3',
        'data_v6/cache/ticks/aug_w-2', 
        'data_v6/cache/ticks/aug_w-1',
        'data_v6/cache/beacons/sep_w1',
        'data_v6/cache/beacons/sep_w2',
        'data_v6/cache/beacons/sep_w3',
        'data_v6/cache/ticks/sep_w1',
        'data_v6/cache/ticks/sep_w2',
        'data_v6/cache/ticks/sep_w3'
    }
    
    unused_folders = []
    
    cache_base = "data_v6/cache"
    if not os.path.exists(cache_base):
        print(f"❌ {cache_base} does not exist")
        return unused_folders
    
    # Check beacons directory
    beacons_dir = os.path.join(cache_base, "beacons")
    if os.path.exists(beacons_dir):
        print(f"📁 Checking {beacons_dir}")
        for item in os.listdir(beacons_dir):
            if "week" in item.lower() or "w" in item.lower():
                folder_path = os.path.join(beacons_dir, item)
                if os.path.isdir(folder_path):
                    full_path = f"data_v6/cache/beacons/{item}"
                    if full_path not in active_directories:
                        print(f"  🔍 Found unused folder: {full_path}")
                        size_mb, file_count = get_directory_size(folder_path)
                        last_modified = get_last_modified(folder_path)
                        
                        unused_folders.append({
                            "path": full_path,
                            "size_mb": round(size_mb, 2),
                            "files": file_count,
                            "last_modified": last_modified
                        })
                        print(f"    Size: {size_mb:.2f} MB, Files: {file_count}, Modified: {last_modified}")
    
    # Check ticks directory
    ticks_dir = os.path.join(cache_base, "ticks")
    if os.path.exists(ticks_dir):
        print(f"📁 Checking {ticks_dir}")
        for item in os.listdir(ticks_dir):
            if "week" in item.lower() or "w" in item.lower():
                folder_path = os.path.join(ticks_dir, item)
                if os.path.isdir(folder_path):
                    full_path = f"data_v6/cache/ticks/{item}"
                    if full_path not in active_directories:
                        print(f"  🔍 Found unused folder: {full_path}")
                        size_mb, file_count = get_directory_size(folder_path)
                        last_modified = get_last_modified(folder_path)
                        
                        unused_folders.append({
                            "path": full_path,
                            "size_mb": round(size_mb, 2),
                            "files": file_count,
                            "last_modified": last_modified
                        })
                        print(f"    Size: {size_mb:.2f} MB, Files: {file_count}, Modified: {last_modified}")
    
    print(f"\n📊 Found {len(unused_folders)} unused week folders")
    return unused_folders

def audit_tmp_files():
    """Audit tmp/research_rx/ for old files"""
    print("\n🔍 AUDITING tmp/research_rx/ FOR OLD FILES")
    print("=" * 60)
    
    old_files = []
    cutoff_date = datetime.now() - timedelta(days=7)
    
    tmp_dir = "tmp/research_rx"
    if not os.path.exists(tmp_dir):
        print(f"❌ {tmp_dir} does not exist")
        return old_files
    
    print(f"📁 Checking {tmp_dir} for files older than 7 days")
    print(f"Cutoff date: {cutoff_date.isoformat()}")
    
    for root, dirs, files in os.walk(tmp_dir):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                # Get file modification time
                mtime = os.path.getmtime(file_path)
                file_date = datetime.fromtimestamp(mtime)
                
                if file_date < cutoff_date:
                    file_size = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB
                    
                    old_files.append({
                        "path": file_path,
                        "size_mb": round(file_size, 2),
                        "last_modified": file_date.isoformat()
                    })
                    
                    print(f"  🔍 Old file: {file_path}")
                    print(f"    Size: {file_size:.2f} MB, Modified: {file_date.isoformat()}")
                    
            except (OSError, FileNotFoundError):
                continue
    
    print(f"\n📊 Found {len(old_files)} old files")
    return old_files

def main():
    print("🧹 SAFE DISK CLEANUP AUDIT")
    print("=" * 50)
    print("Memory limit: ≤250 MB, Runtime: ≤3 minutes")
    print(f"Initial memory: {get_memory_usage():.1f} MB")
    print()
    
    start_time = time.time()
    
    # Check for critical directories that should not be touched
    critical_dirs = [
        "data_v6/cache/beacons/sep_w1",
        "data_v6/cache/beacons/sep_w2", 
        "data_v6/cache/beacons/sep_w3",
        "data_v6/cache/ticks/sep_w1",
        "data_v6/cache/ticks/sep_w2",
        "data_v6/cache/ticks/sep_w3"
    ]
    
    print("🛡️ CHECKING CRITICAL DIRECTORIES")
    print("-" * 30)
    for critical_dir in critical_dirs:
        if os.path.exists(critical_dir):
            print(f"✅ {critical_dir} - EXISTS")
        else:
            print(f"❌ {critical_dir} - MISSING")
            print("🚨 HALTING - Critical directory missing!")
            return
    
    print("\n✅ All critical directories present - proceeding with audit")
    
    # Audit unused week folders
    unused_folders = audit_cache_directories()
    
    # Audit old tmp files
    old_tmp_files = audit_tmp_files()
    
    # Generate summary
    summary = {
        "unused_week_folders": unused_folders,
        "old_tmp_files": old_tmp_files
    }
    
    # Runtime and memory check
    runtime = time.time() - start_time
    memory = get_memory_usage()
    
    print(f"\n⏱️ Runtime: {runtime:.2f} seconds")
    print(f"💾 Memory usage: {memory:.1f} MB")
    
    if runtime > 180:  # 3 minutes
        print("⚠️ Runtime exceeded 3 minutes")
    
    if memory > 250:
        print("⚠️ Memory usage exceeded 250 MB")
    
    # Output JSON summary
    print(f"\n📋 AUDIT SUMMARY (JSON)")
    print("=" * 50)
    print(json.dumps(summary, indent=2))
    
    # Calculate total space that could be freed
    total_unused_size = sum(folder["size_mb"] for folder in unused_folders)
    total_old_size = sum(file["size_mb"] for file in old_tmp_files)
    total_potential_savings = total_unused_size + total_old_size
    
    print(f"\n💰 POTENTIAL SPACE SAVINGS")
    print("-" * 30)
    print(f"Unused week folders: {total_unused_size:.2f} MB")
    print(f"Old tmp files: {total_old_size:.2f} MB")
    print(f"Total potential savings: {total_potential_savings:.2f} MB")

if __name__ == "__main__":
    main()



