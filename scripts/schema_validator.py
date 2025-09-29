#!/usr/bin/env python3
"""
Schema Validator for Enhanced Metrics
Validates data structure before processing enhanced metrics
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class SchemaValidator:
    """Validates data schema for enhanced metrics processing"""
    
    # Required columns for enhanced metrics
    REQUIRED_COLUMNS = [
        'ts_exchange', 'best_bid', 'best_ask',
        'bid_sz', 'ask_sz',            # L1 sizes
        'last_px', 'last_sz',          # trade price/size
        'venue_id'
    ]
    
    # Derived columns (computed on write)
    DERIVED_COLUMNS = ['mid_px', 'spread_bps', 'imbalance']
    
    def validate_schema(self, data: Dict[str, pd.DataFrame]) -> Tuple[bool, Dict[str, Any]]:
        """Validate schema for enhanced metrics processing"""
        
        if not data:
            return False, {"error": "No data provided", "schema_status": "incomplete"}
        
        # Check each venue's schema
        venue_results = {}
        all_venues_complete = True
        missing_fields = set()
        
        for venue, df in data.items():
            if len(df) == 0:
                venue_results[venue] = {
                    "status": "empty",
                    "missing_fields": self.REQUIRED_COLUMNS,
                    "enhanced_metrics": False
                }
                all_venues_complete = False
                missing_fields.update(self.REQUIRED_COLUMNS)
                continue
            
            # Check required columns
            available_columns = set(df.columns)
            required_columns = set(self.REQUIRED_COLUMNS)
            missing_columns = required_columns - available_columns
            
            venue_complete = len(missing_columns) == 0
            
            venue_results[venue] = {
                "status": "complete" if venue_complete else "incomplete",
                "available_fields": len(available_columns),
                "required_fields": len(required_columns),
                "missing_fields": list(missing_columns),
                "enhanced_metrics": venue_complete
            }
            
            if not venue_complete:
                all_venues_complete = False
                missing_fields.update(missing_columns)
        
        # Overall schema status
        schema_status = "complete" if all_venues_complete else "incomplete"
        enhanced_metrics_available = all_venues_complete
        
        result = {
            "schema_status": schema_status,
            "enhanced_metrics": enhanced_metrics_available,
            "total_venues": len(data),
            "complete_venues": sum(1 for v in venue_results.values() if v["status"] == "complete"),
            "missing_fields": list(missing_fields),
            "venue_details": venue_results
        }
        
        # Log schema summary
        if enhanced_metrics_available:
            logger.info(f"[SCHEMA:SUMMARY] enhanced=ON venues={len(data)}/{len(data)}")
        else:
            logger.warning(f"[SCHEMA:FAIL] enhanced=OFF missing={list(missing_fields)} venues={result['complete_venues']}/{len(data)}")
        
        return enhanced_metrics_available, result
    
    def create_schema_stub(self, symbol: str, date: str, time_range: str, schema_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create a schema-compliant stub for incomplete data"""
        
        stub = {
            "timestamp": pd.Timestamp.now(timezone='UTC').isoformat(),
            "symbol": symbol,
            "date": date,
            "time_range": time_range,
            "provenance": "REAL",
            "regulatory_grade": True,
            "schema_status": "incomplete",
            "enhanced_metrics": False,
            "schema_validation": schema_result,
            "metrics": {},
            "cross_venue": {
                "lead_lag": {},
                "infoshare": {},
                "leadership_shares": {
                    "volume_weighted": {},
                    "price_impact": {},
                    "information_leadership": {},
                    "venue_specialization": {}
                }
            }
        }
        
        # Add basic metrics for venues with complete data
        for venue, venue_info in schema_result.get("venue_details", {}).items():
            if venue_info["status"] == "complete":
                stub["metrics"][venue] = {
                    "vwap": np.nan,
                    "highs_lows": {"high_24h": np.nan, "low_24h": np.nan},
                    "session": "Unknown",
                    "volatility_1m": np.nan,
                    "spread_metrics": {"spread_bps_mean": np.nan, "spread_bps_std": np.nan},
                    "liquidity_metrics": {
                        "liquidity_score": np.nan,
                        "depth_imbalance": np.nan,
                        "liquidity_volatility": np.nan,
                        "market_impact": np.nan,
                        "liquidity_ratio": np.nan
                    }
                }
        
        return stub

def main():
    """Test schema validator"""
    validator = SchemaValidator()
    
    # Test with sample data
    print("Schema validator ready")
    print(f"Required columns: {validator.REQUIRED_COLUMNS}")
    print(f"Derived columns: {validator.DERIVED_COLUMNS}")

if __name__ == "__main__":
    main()
