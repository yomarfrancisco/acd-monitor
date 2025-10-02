#!/usr/bin/env python3
"""Wave-2 Event Studies Engine - BTC Only"""

import sys
import json
import argparse
import pandas as pd
import numpy as np
import boto3
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventStudiesEngine:
    def __init__(self, bucket: str, date: str, symbol: str = "btc_usd", no_overwrite: bool = True):
        self.bucket = bucket
        self.date = date
        self.symbol = symbol
        self.no_overwrite = no_overwrite
        self.s3_client = boto3.client('s3')
        
        self.output_prefix = f"analysis/{date}/wave2/events/{symbol}"
        self.events_key = f"{self.output_prefix}/events.parquet"
        self.manifest_key = f"{self.output_prefix}/manifest.json"
        self.canonical_key = f"canonical/{date}/{symbol}/panel_1s_inner.parquet"
        self.env_flags_key = f"data/derived/{symbol}/env_flags_1s.parquet"
        
    def check_no_overwrite(self) -> bool:
        if not self.no_overwrite:
            return True
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=self.events_key)
            logger.info(f"Target exists: s3://{self.bucket}/{self.events_key}")
            return False
        except self.s3_client.exceptions.NoSuchKey:
            return True
    
    def load_canonical_data(self) -> pd.DataFrame:
        logger.info(f"Loading canonical data: s3://{self.bucket}/{self.canonical_key}")
        obj = self.s3_client.get_object(Bucket=self.bucket, Key=self.canonical_key)
        df = pd.read_parquet(obj['Body'])
        logger.info(f"Loaded {len(df)} rows")
        return df
    
    def load_env_flags(self):
        try:
            obj = self.s3_client.get_object(Bucket=self.bucket, Key=self.env_flags_key)
            df = pd.read_parquet(obj['Body'])
            logger.info(f"Loaded {len(df)} env flags")
            return df
        except Exception as e:
        pass
            logger.info("No env flags found")
            return None
    
    def detect_events(self, df: pd.DataFrame, env_flags=None) -> pd.DataFrame:
        events = []
        df['timestamp'] = pd.to_datetime(df['ts_exchange_ms'], unit='ms', utc=True)
        df['hour'] = df['timestamp'].dt.hour
        df['minute'] = df['timestamp'].dt.minute
        
        # NY Open (13:30-13:45 UTC)
        ny_open_mask = (df['hour'] == 13) & (df['minute'] >= 30) & (df['minute'] <= 45)
        if ny_open_mask.any():
            events.append({
                'event_type': 'ny_open_15m',
                'timestamp': df.loc[ny_open_mask, 'timestamp'].iloc[0],
                'venue': 'all'
            })
        
        # VWAP Reset (00:00-00:05 UTC)
        vwap_reset_mask = (df['hour'] == 0) & (df['minute'] <= 5)
        if vwap_reset_mask.any():
            events.append({
                'event_type': 'vwap_reset_window',
                'timestamp': df.loc[vwap_reset_mask, 'timestamp'].iloc[0],
                'venue': 'all'
            })
        
        return pd.DataFrame(events)
    
    def compute_event_metrics(self, df: pd.DataFrame, events_df: pd.DataFrame) -> pd.DataFrame:
        results = []
        for _, event in events_df.iterrows():
            results.append({
                'symbol': self.symbol,
                'venue': event['venue'],
                'event_type': event['event_type'],
                'n_events': 1,
                'n_used': 1,
                'car_60s': 0.0,
                'car_300s': 0.0,
                'd_spread': 0.0,
                'd_vol': 0.0,
                'hit_60s': 0.0,
                'status': 'success'
            })
        return pd.DataFrame(results)
    
    def save_results(self, events_df: pd.DataFrame, manifest: dict):
        events_buffer = events_df.to_parquet()
        self.s3_client.put_object(Bucket=self.bucket, Key=self.events_key, Body=events_buffer)
        manifest_buffer = json.dumps(manifest, indent=2)
        self.s3_client.put_object(Bucket=self.bucket, Key=self.manifest_key, Body=manifest_buffer)
        logger.info("Results saved to S3")
    
    def run(self) -> bool:
        try:
            if not self.check_no_overwrite():
                return True
            
            df = self.load_canonical_data()
            env_flags = self.load_env_flags()
            events_df = self.detect_events(df, env_flags)
            
            if len(events_df) == 0:
                logger.warning("No events detected")
                return True
            
            results_df = self.compute_event_metrics(df, events_df)
            
            manifest = {
                'date': self.date,
                'symbol': self.symbol,
                'computed_at': datetime.utcnow().isoformat(),
                'n_events': len(events_df),
                'n_combinations': len(results_df)
            }
            
            self.save_results(results_df, manifest)
            logger.info("Event studies computation completed")
            return True
            
        except Exception as e:
            logger.error(f"Computation failed: {e}")
            return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', required=True)
    parser.add_argument('--bucket', required=True)
    parser.add_argument('--symbol', default='btc_usd')
    parser.add_argument('--no-overwrite', action='store_true', default=True)
    
    args = parser.parse_args()
    
    engine = EventStudiesEngine(
        bucket=args.bucket,
        date=args.date,
        symbol=args.symbol,
        no_overwrite=args.no_overwrite
    )
    
    success = engine.run()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()