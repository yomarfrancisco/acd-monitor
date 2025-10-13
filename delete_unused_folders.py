#!/usr/bin/env python3
"""
Safe deletion of unused week folders identified in audit
Only deletes the specific folders identified as safe to remove
"""

import os
import shutil
import time

def delete_unused_folders():
    """Delete only the unused folders identified in the audit"""
    print("🗑️ DELETING UNUSED WEEK FOLDERS")
    print("=" * 50)
    
    # Only the specific folders identified in the audit
    unused_folders = [
        "data_v6/cache/beacons/week-4",
        "data_v6/cache/beacons/week-3", 
        "data_v6/cache/beacons/week-minus1",
        "data_v6/cache/beacons/week-minus2"
    ]
    
    deleted_count = 0
    total_size_freed = 0
    
    for folder_path in unused_folders:
        if os.path.exists(folder_path):
            try:
                # Calculate size before deletion
                folder_size = 0
                for dirpath, dirnames, filenames in os.walk(folder_path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            folder_size += os.path.getsize(filepath)
                        except (OSError, FileNotFoundError):
                            continue
                
                # Delete the folder
                shutil.rmtree(folder_path)
                size_mb = folder_size / (1024 * 1024)
                total_size_freed += size_mb
                deleted_count += 1
                
                print(f"✅ Deleted: {folder_path}")
                print(f"   Size freed: {size_mb:.2f} MB")
                
            except Exception as e:
                print(f"❌ Failed to delete {folder_path}: {e}")
        else:
            print(f"⚠️ Folder not found: {folder_path}")
    
    print(f"\n📊 DELETION SUMMARY")
    print("-" * 30)
    print(f"Folders deleted: {deleted_count}/{len(unused_folders)}")
    print(f"Total space freed: {total_size_freed:.2f} MB")
    
    # Verify critical directories still exist
    print(f"\n🛡️ VERIFYING CRITICAL DIRECTORIES")
    print("-" * 30)
    critical_dirs = [
        "data_v6/cache/beacons/sep_w1",
        "data_v6/cache/beacons/sep_w2", 
        "data_v6/cache/beacons/sep_w3",
        "data_v6/cache/ticks/sep_w1",
        "data_v6/cache/ticks/sep_w2",
        "data_v6/cache/ticks/sep_w3"
    ]
    
    all_critical_exist = True
    for critical_dir in critical_dirs:
        if os.path.exists(critical_dir):
            print(f"✅ {critical_dir} - EXISTS")
        else:
            print(f"❌ {critical_dir} - MISSING")
            all_critical_exist = False
    
    if all_critical_exist:
        print(f"\n✅ DELETION COMPLETE - All critical directories intact")
    else:
        print(f"\n🚨 WARNING - Some critical directories missing!")

if __name__ == "__main__":
    delete_unused_folders()



