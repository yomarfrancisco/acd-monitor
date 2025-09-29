# Synthetic Positive Control Plan

**Date**: 2025-09-29  
**Purpose**: Verify detectors fire when coordination is present  

## **Injection Types**

### **1. Lead-Lag Injection**
- **Method**: Add systematic +50ms delay to one venue
- **Target**: Test Lead-Lag v2 detector sensitivity
- **Expected**: ρ ≥ 0.12 threshold should be exceeded

### **2. Synchronization Injection**
- **Method**: All venues jump together at pre-set intervals
- **Target**: Test InfoShare v2 detector sensitivity  
- **Expected**: One venue should exceed 70% dominance

### **3. Dominance Spike Injection**
- **Method**: One venue >70% info share for a block
- **Target**: Test InfoShare v2 detector sensitivity
- **Expected**: Clear dominance pattern detection

## **Implementation Strategy**

1. **Base Dataset**: Use existing 12:00-14:00 UTC windows
2. **Injection Points**: 
   - Lead-Lag: Apply to coinbase venue
   - Sync: Apply to all venues at 5-minute intervals
   - Dominance: Apply to binance venue for 10-minute blocks
3. **Validation**: Run full detector suite on modified datasets
4. **Comparison**: Compare null vs injected results

## **Success Criteria**

- **Lead-Lag**: ρ ≥ 0.12 detected in injected data
- **InfoShare**: ≥70% dominance detected in injected data  
- **Null Comparison**: Original data shows null results
- **Detector Sensitivity**: Clear signal detection in synthetic data
