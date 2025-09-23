# UI Copy Mapping Proposal - Bank to Crypto Transition

**Generated**: 2024-12-19  
**Purpose**: Map current bank-case labels to crypto terminology for ACD v1.9+  
**Status**: PROPOSAL ONLY - No UI changes implemented yet

## Overview

This document proposes terminology changes to align the ACD dashboard with crypto market context while maintaining the same analytical framework. All changes preserve the underlying data structure and API contracts.

## Copy Mapping Table

| Location (screenshot ref) | Current text/label | Proposed crypto label | Data source (endpoint/field) | Reasoning (tie to v1.9+ docs) |
|---------------------------|-------------------|----------------------|------------------------------|-------------------------------|
| Diagnostic card title | Algorithmic Cartel Diagnostic | Algorithmic Coordination Diagnostic | `/api/risk/summary.score` & `.band` | Aligns with ACD terminology, consistent with v1.9+ |
| Axis label | SA Bank CDS Spread % | Exchange Liquidity Spread % | `/api/metrics/overview.priceStability.value` (proxy term) | Crypto context; matches "price stability/synchronization" KPIs |
| Tooltip "SARB Rate Cut" moment | Macro Event (SARB Rate Cut) | On-chain/Market Event (e.g., BTC Halving, SEC action) | `/api/events.items[].message` | Replace bank macro with crypto events |
| Entities (FNB/ABSA/…) | Bank names | Exchanges (Binance.US, Coinbase, Kraken) | `/api/events.items[].entities` | Pilot scope: US exchanges per v1.9+ |
| YTD Price Leader | YTD Price Leader | YTD Liquidity Leader (or YTD Market Share Leader) | evidence export / events | Keeps UX intent; crypto-relevant |

## Example Tooltip Rewrites

### 1. Risk Summary Tooltip
**Current**: "Low risk detected in SA banking sector coordination patterns"
**Proposed**: "Low risk detected in US crypto exchange coordination patterns"
**JSON Source**: `/api/risk/summary`
```json
{
  "score": 14,
  "band": "LOW",
  "confidence": 97,
  "source": {
    "name": "Algorithmic Coordination Detection Engine"
  }
}
```

### 2. Price Stability KPI
**Current**: "Price stability across major SA banks within normal ranges"
**Proposed**: "Price stability across major US exchanges within normal ranges"
**JSON Source**: `/api/metrics/overview`
```json
{
  "items": [
    {
      "key": "stability",
      "label": "Price Stability",
      "score": 72,
      "note": "Normal spread volatility"
    }
  ]
}
```

### 3. Market Event Tooltip
**Current**: "SARB rate cut announcement triggered coordinated response"
**Proposed**: "SEC regulatory announcement triggered coordinated response"
**JSON Source**: `/api/events`
```json
{
  "items": [
    {
      "type": "REGIME_SWITCH",
      "title": "Regime switch",
      "description": "Market regime transition detected",
      "severity": "LOW"
    }
  ]
}
```

### 4. Entity Coordination Tooltip
**Current**: "FNB leading price movements, followed by ABSA and Standard Bank"
**Proposed**: "Binance.US leading price movements, followed by Coinbase and Kraken"
**JSON Source**: `/api/events`
```json
{
  "items": [
    {
      "affects": ["Binance.US", "Coinbase", "Kraken", "Gemini"]
    }
  ]
}
```

### 5. Evidence Export Tooltip
**Current**: "Export comprehensive SA banking coordination analysis"
**Proposed**: "Export comprehensive US crypto exchange coordination analysis"
**JSON Source**: `/api/evidence/export`
```json
{
  "summary": "Algorithmic Coordination Diagnostic - Evidence Package",
  "methodology": "Brief 55+ Framework implementation"
}
```

## Implementation Notes

### Data Structure Preservation
- All API endpoints remain unchanged
- JSON schemas maintain compatibility
- Only display labels and tooltips change
- Backend data processing unchanged

### Crypto Context Alignment
- **Exchanges**: Binance.US, Coinbase, Kraken, Gemini (US-focused)
- **Events**: SEC actions, BTC halving, regulatory announcements
- **Metrics**: Liquidity spreads, market share, coordination patterns
- **Timeframes**: Maintain existing (30d, 6m, 1y, YTD)

### v1.9+ Compliance
- Terminology aligns with ACD v1.9+ documentation
- Maintains analytical framework integrity
- Preserves risk assessment methodology
- Keeps evidence export structure

## Approval Process

1. **Review**: Stakeholders review proposed terminology changes
2. **Approval**: Sign-off on crypto context alignment
3. **Implementation**: Update UI components with approved copy
4. **Testing**: Verify all tooltips and labels display correctly
5. **Deployment**: Deploy with updated terminology

## Risk Mitigation

- **Backward Compatibility**: All API contracts preserved
- **Data Integrity**: No changes to data processing logic
- **User Experience**: Maintains familiar interface patterns
- **Documentation**: Update user guides with new terminology

---

**This proposal maintains the analytical rigor of the ACD system while adapting the presentation layer for crypto market context. No changes will be implemented until approved by stakeholders.**
