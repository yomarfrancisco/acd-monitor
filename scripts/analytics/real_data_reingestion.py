#!/usr/bin/env python3
"""
Real Data Re-ingestion: Direct S3 Parquet Queries
=================================================

This script re-ingests real S3 snapshots using DuckDB for zero-copy queries,
enabling analysis without downloading data locally.
"""

import duckdb
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple
import logging
from datetime import datetime
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealDataReingestion:
    """Re-ingest real S3 snapshots using DuckDB zero-copy queries."""
    
    def __init__(self, output_dir: str = "data/derived/btc_usd_real"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # S3 configuration
        self.bucket_name = 'acd-monitor-snapshots'
        self.s3_prefix = 'snapshots/BTC-USD/'
        
        # Initialize DuckDB connection
        self.conn = duckdb.connect()
        
        # Configure DuckDB for S3 access
        self.conn.execute("INSTALL httpfs;")
        self.conn.execute("LOAD httpfs;")
        self.conn.execute("SET s3_region='us-east-1';")
        
        # Configure AWS credentials from environment
        import os
        aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        aws_session_token = os.getenv('AWS_SESSION_TOKEN')
        
        if aws_access_key and aws_secret_key:
            self.conn.execute(f"SET s3_access_key_id='{aws_access_key}';")
            self.conn.execute(f"SET s3_secret_access_key='{aws_secret_key}';")
            if aws_session_token:
                self.conn.execute(f"SET s3_session_token='{aws_session_token}';")
    
    def get_s3_file_list(self) -> List[str]:
        """Get list of S3 parquet files."""
        logger.info("Getting S3 file list...")
        
        # Use DuckDB to list S3 files
        query = f"""
        SELECT file_path
        FROM glob('s3://{self.bucket_name}/{self.s3_prefix}**/*.parquet')
        ORDER BY file_path
        """
        
        try:
            result = self.conn.execute(query).fetchall()
            file_paths = [row[0] for row in result]
            logger.info(f"✅ Found {len(file_paths)} parquet files")
            return file_paths
            
        except Exception as e:
            logger.error(f"❌ Failed to list S3 files: {e}")
            return []
    
    def get_data_coverage(self) -> Dict[str, Any]:
        """Get data coverage statistics."""
        logger.info("Analyzing data coverage...")
        
        coverage_query = f"""
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT venue) as unique_venues,
            MIN(ts_exchange) as min_timestamp,
            MAX(ts_exchange) as max_timestamp,
            COUNT(DISTINCT DATE_TRUNC('day', TO_TIMESTAMP(ts_exchange/1000))) as unique_days
        FROM read_parquet('s3://{self.bucket_name}/{self.s3_prefix}**/*.parquet')
        """
        
        try:
            result = self.conn.execute(coverage_query).fetchone()
            coverage = {
                'total_records': result[0],
                'unique_venues': result[1],
                'min_timestamp': result[2],
                'max_timestamp': result[3],
                'unique_days': result[4]
            }
            
            logger.info(f"✅ Data coverage: {coverage['total_records']} records, {coverage['unique_venues']} venues, {coverage['unique_days']} days")
            return coverage
            
        except Exception as e:
            logger.error(f"❌ Failed to get data coverage: {e}")
            return {}
    
    def get_venue_coverage(self) -> pd.DataFrame:
        """Get venue-specific coverage statistics."""
        logger.info("Analyzing venue coverage...")
        
        venue_query = f"""
        SELECT 
            venue,
            COUNT(*) as record_count,
            MIN(ts_exchange) as min_timestamp,
            MAX(ts_exchange) as max_timestamp,
            COUNT(DISTINCT DATE_TRUNC('day', TO_TIMESTAMP(ts_exchange/1000))) as unique_days
        FROM read_parquet('s3://{self.bucket_name}/{self.s3_prefix}**/*.parquet')
        GROUP BY venue
        ORDER BY record_count DESC
        """
        
        try:
            df = self.conn.execute(venue_query).df()
            logger.info(f"✅ Venue coverage analysis complete: {len(df)} venues")
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to get venue coverage: {e}")
            return pd.DataFrame()
    
    def create_aligned_panel(self, start_date: str = '2025-09-28', end_date: str = '2025-09-30') -> pd.DataFrame:
        """Create aligned panel from real S3 data."""
        logger.info(f"Creating aligned panel from {start_date} to {end_date}...")
        
        # Query to create aligned panel
        panel_query = f"""
        WITH venue_data AS (
            SELECT 
                venue,
                ts_exchange,
                best_bid,
                best_ask,
                last_px,
                bid_sz,
                ask_sz,
                trade_sz,
                (best_bid + best_ask) / 2 as mid_price
            FROM read_parquet('s3://{self.bucket_name}/{self.s3_prefix}**/*.parquet')
            WHERE DATE_TRUNC('day', TO_TIMESTAMP(ts_exchange/1000)) BETWEEN '{start_date}' AND '{end_date}'
        ),
        aligned_data AS (
            SELECT 
                ts_exchange,
                MAX(CASE WHEN venue = 'binance' THEN mid_price END) as mid_binance,
                MAX(CASE WHEN venue = 'coinbase' THEN mid_price END) as mid_coinbase,
                MAX(CASE WHEN venue = 'kraken' THEN mid_price END) as mid_kraken,
                MAX(CASE WHEN venue = 'okx' THEN mid_price END) as mid_okx,
                MAX(CASE WHEN venue = 'bybit' THEN mid_price END) as mid_bybit,
                MAX(CASE WHEN venue = 'binance' THEN best_bid END) as bid_binance,
                MAX(CASE WHEN venue = 'coinbase' THEN best_bid END) as bid_coinbase,
                MAX(CASE WHEN venue = 'kraken' THEN best_bid END) as bid_kraken,
                MAX(CASE WHEN venue = 'okx' THEN best_bid END) as bid_okx,
                MAX(CASE WHEN venue = 'bybit' THEN best_bid END) as bid_bybit,
                MAX(CASE WHEN venue = 'binance' THEN best_ask END) as ask_binance,
                MAX(CASE WHEN venue = 'coinbase' THEN best_ask END) as ask_coinbase,
                MAX(CASE WHEN venue = 'kraken' THEN best_ask END) as ask_kraken,
                MAX(CASE WHEN venue = 'okx' THEN best_ask END) as ask_okx,
                MAX(CASE WHEN venue = 'bybit' THEN best_ask END) as ask_bybit
            FROM venue_data
            GROUP BY ts_exchange
            HAVING COUNT(DISTINCT venue) >= 3  -- Require at least 3 venues
        )
        SELECT *
        FROM aligned_data
        ORDER BY ts_exchange
        """
        
        try:
            df = self.conn.execute(panel_query).df()
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['ts_exchange'], unit='ms')
            df = df.set_index('timestamp')
            
            logger.info(f"✅ Aligned panel created: {len(df)} observations")
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to create aligned panel: {e}")
            return pd.DataFrame()
    
    def save_aligned_panel(self, df: pd.DataFrame) -> None:
        """Save aligned panel to local parquet."""
        logger.info("Saving aligned panel...")
        
        if df.empty:
            logger.warning("No data to save")
            return
        
        # Save to parquet
        output_path = self.output_dir / 'panel_1s_inner_real.parquet'
        df.to_parquet(output_path)
        
        # Save metadata
        metadata = {
            'creation_date': datetime.now().isoformat(),
            'total_observations': len(df),
            'date_range': {
                'start': df.index.min().isoformat(),
                'end': df.index.max().isoformat()
            },
            'venues': [col for col in df.columns if col.startswith('mid_')],
            'data_source': 'real_s3_snapshots',
            'methodology': 'duckdb_zero_copy_query'
        }
        
        with open(self.output_dir / 'panel_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✅ Aligned panel saved: {output_path}")
    
    def validate_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate data quality of aligned panel."""
        logger.info("Validating data quality...")
        
        if df.empty:
            return {'error': 'No data to validate'}
        
        quality_metrics = {
            'total_observations': len(df),
            'date_range': {
                'start': df.index.min().isoformat(),
                'end': df.index.max().isoformat()
            },
            'venue_coverage': {},
            'missing_data': {},
            'data_quality_score': 0.0
        }
        
        # Check venue coverage
        venue_cols = [col for col in df.columns if col.startswith('mid_')]
        for venue_col in venue_cols:
            venue = venue_col.replace('mid_', '')
            non_null_count = df[venue_col].notna().sum()
            coverage_pct = (non_null_count / len(df)) * 100
            quality_metrics['venue_coverage'][venue] = {
                'coverage_pct': coverage_pct,
                'non_null_count': non_null_count
            }
        
        # Check missing data
        for col in df.columns:
            missing_count = df[col].isna().sum()
            missing_pct = (missing_count / len(df)) * 100
            quality_metrics['missing_data'][col] = {
                'missing_count': missing_count,
                'missing_pct': missing_pct
            }
        
        # Calculate overall data quality score
        avg_coverage = np.mean([metrics['coverage_pct'] for metrics in quality_metrics['venue_coverage'].values()])
        avg_missing = np.mean([metrics['missing_pct'] for metrics in quality_metrics['missing_data'].values()])
        quality_score = (avg_coverage / 100) * (1 - avg_missing / 100)
        quality_metrics['data_quality_score'] = quality_score
        
        logger.info(f"✅ Data quality validation complete: {quality_score:.2f} score")
        return quality_metrics
    
    def run_reingestion(self) -> bool:
        """Run complete real data re-ingestion."""
        logger.info("Starting real data re-ingestion from S3...")
        
        try:
            # Get data coverage
            coverage = self.get_data_coverage()
            if not coverage:
                logger.error("❌ Failed to get data coverage")
                return False
            
            # Get venue coverage
            venue_coverage = self.get_venue_coverage()
            if venue_coverage.empty:
                logger.error("❌ Failed to get venue coverage")
                return False
            
            # Create aligned panel
            df = self.create_aligned_panel()
            if df.empty:
                logger.error("❌ Failed to create aligned panel")
                return False
            
            # Validate data quality
            quality_metrics = self.validate_data_quality(df)
            
            # Save aligned panel
            self.save_aligned_panel(df)
            
            # Save coverage and quality reports
            with open(self.output_dir / 'data_coverage.json', 'w') as f:
                json.dump(coverage, f, indent=2, default=str)
            
            with open(self.output_dir / 'venue_coverage.json', 'w') as f:
                json.dump(venue_coverage.to_dict('records'), f, indent=2, default=str)
            
            with open(self.output_dir / 'data_quality.json', 'w') as f:
                json.dump(quality_metrics, f, indent=2, default=str)
            
            logger.info("✅ Real data re-ingestion completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Real data re-ingestion failed: {e}")
            return False

def main():
    """Main execution function."""
    reingestion = RealDataReingestion()
    success = reingestion.run_reingestion()
    
    if success:
        print("\n🎉 Real data re-ingestion complete!")
        print("✅ Zero-copy S3 queries successful")
        print("✅ Aligned panel created from real data")
        print("✅ Data quality validated")
    else:
        print("\n❌ Real data re-ingestion failed")
        print("❌ Check logs for details")

if __name__ == "__main__":
    main()
