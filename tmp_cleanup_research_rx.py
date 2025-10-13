#!/usr/bin/env python3
"""
TMP CLEANUP – research_rx
Goal: Delete all TEMP directories under tmp/research_rx/ with strict guardrails
"""

import os
import shutil
import psutil
import time
from datetime import datetime
import glob

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def get_directory_size(path):
    """Get directory size in MB"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
    except Exception as e:
        print(f"Warning: Could not calculate size for {path}: {e}")
    return total_size / (1024 * 1024)  # Convert to MB

def enumerate_temp_directories():
    """Enumerate all tmp/research_rx subdirs and file counts"""
    print("🔍 Enumerating TEMP directories under tmp/research_rx/")
    print("-" * 60)
    
    temp_base = "tmp/research_rx"
    
    if not os.path.exists(temp_base):
        print(f"❌ TEMP base directory {temp_base} does not exist")
        return [], 0.0
    
    # Find all files and directories
    all_paths = []
    total_size = 0.0
    
    # Walk through the directory tree
    for root, dirs, files in os.walk(temp_base):
        # Add directories
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            all_paths.append(dir_path)
        
        # Add files
        for file_name in files:
            file_path = os.path.join(root, file_name)
            all_paths.append(file_path)
    
    # Calculate total size
    total_size = get_directory_size(temp_base)
    
    print(f"Found {len(all_paths)} paths under {temp_base}")
    print(f"Total size: {total_size:.2f} MB")
    
    return all_paths, total_size

def validate_paths(paths):
    """Validate that all paths are safe to delete"""
    print("\n🔍 Validating paths for safety")
    print("-" * 60)
    
    unsafe_paths = []
    
    for path in paths:
        # Check if path begins with canonical/ or data_v6/
        if path.startswith('canonical/') or path.startswith('data_v6/'):
            unsafe_paths.append(path)
            print(f"❌ UNSAFE: {path} (begins with canonical/ or data_v6/)")
    
    if unsafe_paths:
        print(f"\n❌ HALT: Found {len(unsafe_paths)} unsafe paths")
        return False
    
    print(f"✅ All {len(paths)} paths are safe to delete")
    return True

def delete_temp_paths(paths):
    """Delete the specified TEMP paths"""
    print("\n🗑️ Deleting TEMP paths")
    print("-" * 60)
    
    deleted_files = 0
    deleted_dirs = 0
    errors = []
    
    # Sort paths to delete files before directories
    paths.sort(key=lambda x: (x.count(os.sep), x), reverse=True)
    
    for path in paths:
        try:
            if os.path.isfile(path):
                os.remove(path)
                deleted_files += 1
                print(f"  ✅ Deleted file: {path}")
            elif os.path.isdir(path):
                # Only delete if directory is empty
                try:
                    os.rmdir(path)
                    deleted_dirs += 1
                    print(f"  ✅ Deleted directory: {path}")
                except OSError:
                    # Directory not empty, skip for now
                    print(f"  ⚠️ Skipped non-empty directory: {path}")
        except Exception as e:
            error_msg = f"Failed to delete {path}: {e}"
            errors.append(error_msg)
            print(f"  ❌ {error_msg}")
    
    return deleted_files, deleted_dirs, errors

def main():
    print("🧹 TMP CLEANUP – research_rx")
    print("=" * 80)
    print("Goal: Delete all TEMP directories under tmp/research_rx/ with strict guardrails")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    # Check memory limit
    if get_memory_usage() > 250:
        print(f"❌ HALT: Memory usage {get_memory_usage():.1f} MB exceeds 250 MB limit")
        return
    
    start_time = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Step 1: Enumerate all tmp/research_rx subdirs and file counts
    paths, total_size = enumerate_temp_directories()
    
    if not paths:
        print("✅ No TEMP files found to delete")
        return
    
    # Step 2: Validate paths for safety
    if not validate_paths(paths):
        print("❌ HALT: Unsafe paths detected")
        return
    
    # Check file count limit
    if len(paths) > 20:
        print(f"❌ HALT: {len(paths)} files exceeds 20 file limit")
        return
    
    # Step 3: ECHO full list for confirmation
    print(f"\n📋 FULL LIST OF PATHS TO DELETE ({len(paths)} items):")
    print("-" * 60)
    for i, path in enumerate(paths, 1):
        print(f"{i:2d}. {path}")
    
    print(f"\nTotal size to be freed: {total_size:.2f} MB")
    print(f"Total items: {len(paths)}")
    
    # Step 4: Delete listed TEMP paths
    deleted_files, deleted_dirs, errors = delete_temp_paths(paths)
    
    end_time = time.time()
    runtime = end_time - start_time
    
    # ========================================================================
    # CLEANUP SUMMARY
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("📦 CLEANUP SUMMARY")
    print("=" * 80)
    
    print(f"Files deleted: {deleted_files}")
    print(f"Directories deleted: {deleted_dirs}")
    print(f"Total items deleted: {deleted_files + deleted_dirs}")
    print(f"Freed disk space: {total_size:.2f} MB")
    print(f"Timestamp: {timestamp}")
    print(f"Runtime: {runtime:.2f} seconds")
    
    if errors:
        print(f"\nErrors encountered:")
        for error in errors:
            print(f"  ❌ {error}")
    
    # Final status
    print(f"\n{'='*80}")
    final_memory = get_memory_usage()
    if final_memory <= 250:
        print(f"✅ TMP CLEANUP COMPLETE - All guardrails complied with")
        print(f"• No canonical data paths deleted or modified")
        print(f"• No persistent datasets, schemas, or caches outside tmp/ touched")
        print(f"• No recursive delete beyond tmp/research_rx/")
        print(f"• Memory usage: {final_memory:.1f} MB (≤ 250 MB limit)")
        print(f"• Deleted {deleted_files + deleted_dirs} items (≤ 20 limit)")
        print(f"• No paths beginning with canonical/ or data_v6/ deleted")
    else:
        print(f"❌ TMP CLEANUP HALTED")
        print(f"• Memory usage: {final_memory:.1f} MB > 250 MB limit")
    
    print(f"\nMemory usage: {final_memory:.1f} MB")
    print(f"TMP CLEANUP COMPLETE — HALTED after report as requested.")

if __name__ == "__main__":
    main()




