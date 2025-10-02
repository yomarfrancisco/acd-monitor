# ETH Coverage Investigation Report

## **Root Cause Analysis**

### **Problem Statement**
ETH-USD windows are being captured successfully but are missing `meta/coverage.json` files, while BTC-USD windows have coverage data for some windows.

### **Investigation Findings**

#### **1. Capture Pipeline Analysis**
- **Current State**: Continuous capture workflow is using `scripts/capture/capture_window.py` (basic version)
- **Expected State**: Should be using `scripts/capture/capture_window_enhanced.py` (enhanced version with coverage generation)
- **Evidence**: GitHub Actions logs show:
  ```
  python scripts/capture/capture_window.py \
    --symbol ETH-USD \
    --start 2025-09-29T11:00:00Z \
    --end 2025-09-29T11:30:00Z
  ```

#### **2. Sample ETH Window Analysis**
**Window**: `s3://acd-monitor-snapshots/snapshots/ETH-USD/20250929/0830-0900/`

**Files Present**:
- ✅ `OVERLAP.json` (309 bytes)
- ✅ `meta/provenance.json` (138 bytes) 
- ✅ `micro_controls.json` (5MB)
- ✅ `ticks/{venue}/part-0000.parquet` (5 venues, ~400KB each)

**Files Missing**:
- ❌ `meta/coverage.json` (not generated)

#### **3. Code Analysis**
- **`capture_window.py`**: Basic capture script that generates synthetic data but does NOT generate coverage JSON
- **`capture_window_enhanced.py`**: Enhanced script that includes coverage monitoring and generates `meta/coverage.json`

#### **4. Workflow Configuration**
- **Issue**: `.github/workflows/capture_continuous.yml` was updated to use `capture_window_enhanced.py` but the change hasn't been deployed yet
- **Evidence**: Recent capture runs still show `capture_window.py` being called

### **Root Cause Summary**
**Primary Cause**: The continuous capture workflow is using the basic capture script (`capture_window.py`) instead of the enhanced version (`capture_window_enhanced.py`) that includes coverage generation.

**Secondary Cause**: The workflow update to use the enhanced script hasn't been deployed to the running CI environment yet.

### **Impact Assessment**
- **ETH-USD**: 0% coverage data generation (all windows missing `meta/coverage.json`)
- **BTC-USD**: Partial coverage data (some windows have coverage, others don't)
- **Detector Eligibility**: ETH windows cannot pass quality gates without coverage data

### **Recommended Fix**
1. **Immediate**: Deploy the updated workflow that uses `capture_window_enhanced.py`
2. **Verification**: Confirm that new ETH captures generate `meta/coverage.json`
3. **Backfill**: Consider running coverage generation on existing ETH windows if needed

### **Expected Outcome**
After deploying the fix:
- All new ETH-USD captures will generate `meta/coverage.json`
- ETH windows will be eligible for detector sweeps
- Coverage monitoring will work for both BTC and ETH

### **Timeline**
- **Fix Deployment**: Immediate (next workflow run)
- **Verification**: Within 24 hours (next capture cycle)
- **Full Resolution**: 2-3 capture cycles to confirm stability
