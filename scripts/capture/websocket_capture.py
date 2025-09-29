#!/usr/bin/env python3
"""
WebSocket-based Real-time Market Data Capture

This script captures real-time tick data from venue WebSocket feeds,
maintains coverage statistics, and writes to S3 with proper quality gating.
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import boto3
import numpy as np
import pandas as pd
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

# Import custom JSON encoder
class PandasJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for pandas/numpy types."""
    
    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, (np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif hasattr(obj, 'isoformat'):  # datetime objects
            return obj.isoformat()
        return super().default(obj)

logger = logging.getLogger(__name__)

def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')

class VenueWebSocket:
    """WebSocket connection handler for a single venue."""
    
    def __init__(self, venue: str, symbol: str, ring_buffer_size: int = 1000):
        self.venue = venue
        self.symbol = symbol
        self.ring_buffer = deque(maxlen=ring_buffer_size)
        self.connection = None
        self.coverage_stats = {
            'messages_received': 0,
            'gaps_detected': 0,
            'last_message_time': None,
            'connection_drops': 0,
            'start_time': None,
            'end_time': None
        }
        self.venue_config = self._get_venue_config()
    
    def _get_venue_config(self) -> Dict:
        """Get WebSocket configuration for venue."""
        configs = {
            "binance": {
                "url": "wss://stream.binance.com:9443/ws",
                "subscription": {
                    "method": "SUBSCRIBE",
                    "params": [f"{self.symbol.lower().replace('-', '')}@aggTrade", 
                              f"{self.symbol.lower().replace('-', '')}@bookTicker"],
                    "id": 1
                },
                "symbol_mapping": {"BTC-USD": "btcusdt", "ETH-USD": "ethusdt"}
            },
            "coinbase": {
                "url": "wss://ws-feed.exchange.coinbase.com",
                "subscription": {
                    "type": "subscribe",
                    "product_ids": [self.symbol],
                    "channels": ["ticker", "level2"]
                },
                "symbol_mapping": {"BTC-USD": "BTC-USD", "ETH-USD": "ETH-USD"}
            },
            "kraken": {
                "url": "wss://ws.kraken.com",
                "subscription": {
                    "event": "subscribe",
                    "pair": [self.symbol.replace('-', '/')],
                    "subscription": {"name": "trade"}
                },
                "symbol_mapping": {"BTC-USD": "XBT/USD", "ETH-USD": "ETH/USD"}
            },
            "okx": {
                "url": "wss://ws.okx.com:8443/ws/v5/public",
                "subscription": {
                    "op": "subscribe",
                    "args": [
                        {"channel": "tickers", "instId": self.symbol.replace('-', '-')},
                        {"channel": "books", "instId": self.symbol.replace('-', '-')}
                    ]
                },
                "symbol_mapping": {"BTC-USD": "BTC-USDT", "ETH-USD": "ETH-USDT"}
            },
            "bybit": {
                "url": "wss://stream.bybit.com/v5/public/spot",
                "subscription": {
                    "op": "subscribe",
                    "args": [f"tickers.{self.symbol.replace('-', '')}", f"orderbook.1.{self.symbol.replace('-', '')}"]
                },
                "symbol_mapping": {"BTC-USD": "BTCUSDT", "ETH-USD": "ETHUSDT"}
            }
        }
        return configs.get(self.venue, {})
    
    async def connect(self) -> bool:
        """Connect to venue WebSocket."""
        try:
            self.connection = await websockets.connect(
                self.venue_config["url"],
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            # Send subscription message
            await self.connection.send(json.dumps(self.venue_config["subscription"]))
            
            self.coverage_stats['start_time'] = datetime.utcnow()
            logger.info(f"Connected to {self.venue} WebSocket")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to {self.venue}: {e}")
            return False
    
    async def listen(self, duration_seconds: int = 1800):
        """Listen for messages for specified duration."""
        try:
            async for message in self.connection:
                await self._process_message(message)
                
                # Check if we've reached the duration
                if self.coverage_stats['start_time']:
                    elapsed = (datetime.utcnow() - self.coverage_stats['start_time']).total_seconds()
                    if elapsed >= duration_seconds:
                        break
                        
        except ConnectionClosed:
            logger.warning(f"Connection closed for {self.venue}")
            self.coverage_stats['connection_drops'] += 1
        except WebSocketException as e:
            logger.error(f"WebSocket error for {self.venue}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error for {self.venue}: {e}")
        finally:
            self.coverage_stats['end_time'] = datetime.utcnow()
    
    async def _process_message(self, message: str):
        """Process incoming WebSocket message."""
        try:
            data = json.loads(message)
            timestamp = datetime.utcnow()
            
            # Update coverage stats
            self.coverage_stats['messages_received'] += 1
            self.coverage_stats['last_message_time'] = timestamp
            
            # Parse message based on venue
            tick_data = self._parse_venue_message(data)
            if tick_data:
                self.ring_buffer.append(tick_data)
                
        except Exception as e:
            logger.error(f"Error processing message from {self.venue}: {e}")
    
    def _parse_venue_message(self, data: Dict) -> Optional[Dict]:
        """Parse venue-specific message format."""
        try:
            if self.venue == "binance":
                return self._parse_binance_message(data)
            elif self.venue == "coinbase":
                return self._parse_coinbase_message(data)
            elif self.venue == "kraken":
                return self._parse_kraken_message(data)
            elif self.venue == "okx":
                return self._parse_okx_message(data)
            elif self.venue == "bybit":
                return self._parse_bybit_message(data)
        except Exception as e:
            logger.error(f"Error parsing {self.venue} message: {e}")
        return None
    
    def _parse_binance_message(self, data: Dict) -> Optional[Dict]:
        """Parse Binance WebSocket message."""
        if 'e' in data:  # Trade event
            return {
                'ts_exchange': pd.to_datetime(data['E'], unit='ms'),
                'last_px': float(data['p']),
                'last_sz': float(data['q']),
                'trade_sign': 1 if data['m'] else -1,
                'venue_id': self.venue
            }
        elif 'b' in data:  # Book ticker
            return {
                'ts_exchange': pd.to_datetime(data['E'], unit='ms'),
                'best_bid': float(data['b']),
                'best_ask': float(data['a']),
                'bid_sz': float(data['B']),
                'ask_sz': float(data['A']),
                'venue_id': self.venue
            }
        return None
    
    def _parse_coinbase_message(self, data: Dict) -> Optional[Dict]:
        """Parse Coinbase WebSocket message."""
        if data.get('type') == 'ticker':
            return {
                'ts_exchange': pd.to_datetime(data['time']),
                'best_bid': float(data['best_bid']),
                'best_ask': float(data['best_ask']),
                'last_px': float(data['price']),
                'venue_id': self.venue
            }
        return None
    
    def _parse_kraken_message(self, data: Dict) -> Optional[Dict]:
        """Parse Kraken WebSocket message."""
        if isinstance(data, list) and len(data) > 1:
            return {
                'ts_exchange': pd.to_datetime(data[2], unit='s'),
                'last_px': float(data[0]),
                'last_sz': float(data[1]),
                'venue_id': self.venue
            }
        return None
    
    def _parse_okx_message(self, data: Dict) -> Optional[Dict]:
        """Parse OKX WebSocket message."""
        if 'data' in data:
            for item in data['data']:
                return {
                    'ts_exchange': pd.to_datetime(item['ts'], unit='ms'),
                    'best_bid': float(item.get('bidPx', 0)),
                    'best_ask': float(item.get('askPx', 0)),
                    'last_px': float(item.get('last', 0)),
                    'venue_id': self.venue
                }
        return None
    
    def _parse_bybit_message(self, data: Dict) -> Optional[Dict]:
        """Parse Bybit WebSocket message."""
        if 'data' in data:
            item = data['data']
            return {
                'ts_exchange': pd.to_datetime(item['ts'], unit='ms'),
                'best_bid': float(item.get('bid1Price', 0)),
                'best_ask': float(item.get('ask1Price', 0)),
                'last_px': float(item.get('lastPrice', 0)),
                'venue_id': self.venue
            }
        return None
    
    def get_coverage_percentage(self) -> float:
        """Calculate coverage percentage for the venue."""
        if not self.coverage_stats['start_time'] or not self.coverage_stats['end_time']:
            return 0.0
        
        duration = (self.coverage_stats['end_time'] - self.coverage_stats['start_time']).total_seconds()
        expected_messages = duration  # 1 message per second expected
        
        if expected_messages == 0:
            return 0.0
        
        return min(100.0, (self.coverage_stats['messages_received'] / expected_messages) * 100)
    
    async def close(self):
        """Close WebSocket connection."""
        if self.connection:
            await self.connection.close()

class WebSocketCapture:
    """Main WebSocket capture coordinator."""
    
    def __init__(self, symbol: str, venues: List[str], bucket: str, prefix: str):
        self.symbol = symbol
        self.venues = venues
        self.bucket = bucket
        self.prefix = prefix
        self.venue_connections = {}
        self.s3_client = boto3.client('s3')
    
    async def capture_window(self, start_time: datetime, end_time: datetime) -> Dict:
        """Capture a 30-minute window using WebSocket connections."""
        logger.info(f"Capturing {self.symbol} from {start_time} to {end_time}")
        
        # Create venue connections
        for venue in self.venues:
            self.venue_connections[venue] = VenueWebSocket(venue, self.symbol)
        
        # Connect to all venues
        connection_tasks = []
        for venue, connection in self.venue_connections.items():
            task = asyncio.create_task(connection.connect())
            connection_tasks.append(task)
        
        # Wait for all connections
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Check connection success
        successful_venues = []
        for i, result in enumerate(connection_results):
            venue = self.venues[i]
            if isinstance(result, Exception):
                logger.error(f"Failed to connect to {venue}: {result}")
            elif result:
                successful_venues.append(venue)
                logger.info(f"Successfully connected to {venue}")
        
        if len(successful_venues) < 3:
            logger.error(f"Only {len(successful_venues)} venues connected, need ≥3")
            return {"success": False, "reason": "insufficient_venues"}
        
        # Listen for data
        duration_seconds = int((end_time - start_time).total_seconds())
        listen_tasks = []
        
        for venue in successful_venues:
            task = asyncio.create_task(
                self.venue_connections[venue].listen(duration_seconds)
            )
            listen_tasks.append(task)
        
        # Wait for all listening to complete
        await asyncio.gather(*listen_tasks, return_exceptions=True)
        
        # Collect data and calculate coverage
        venue_data = {}
        coverage_data = {}
        
        for venue in successful_venues:
            connection = self.venue_connections[venue]
            
            # Convert ring buffer to DataFrame
            if connection.ring_buffer:
                df = pd.DataFrame(list(connection.ring_buffer))
                venue_data[venue] = df
            else:
                venue_data[venue] = pd.DataFrame()
            
            # Calculate coverage
            coverage = connection.get_coverage_percentage()
            coverage_data[venue] = {
                'coverage_percentage': coverage,
                'messages_received': connection.coverage_stats['messages_received'],
                'connection_drops': connection.coverage_stats['connection_drops'],
                'start_time': connection.coverage_stats['start_time'].isoformat() if connection.coverage_stats['start_time'] else None,
                'end_time': connection.coverage_stats['end_time'].isoformat() if connection.coverage_stats['end_time'] else None
            }
        
        # Check if we have ≥3 venues with ≥95% coverage
        high_coverage_venues = [v for v, data in coverage_data.items() if data['coverage_percentage'] >= 95.0]
        
        if len(high_coverage_venues) < 3:
            logger.warning(f"Only {len(high_coverage_venues)} venues with ≥95% coverage")
            return {
                "success": False, 
                "reason": "insufficient_coverage",
                "coverage_data": coverage_data
            }
        
        # Write to S3
        success = await self._write_to_s3(venue_data, coverage_data, start_time, end_time)
        
        # Close all connections
        for connection in self.venue_connections.values():
            await connection.close()
        
        return {
            "success": success,
            "coverage_data": coverage_data,
            "high_coverage_venues": high_coverage_venues
        }
    
    async def _write_to_s3(self, venue_data: Dict, coverage_data: Dict, 
                          start_time: datetime, end_time: datetime) -> bool:
        """Write captured data to S3."""
        try:
            # Create S3 path
            date_str = start_time.strftime('%Y%m%d')
            time_str = f"{start_time.strftime('%H%M')}-{end_time.strftime('%H%M')}"
            s3_path = f"{self.prefix}/{self.symbol}/{date_str}/{time_str}"
            
            # Write OVERLAP.json
            overlap_data = {
                "start_utc": start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                "end_utc": end_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                "cadences": ["1s"],
                "venues": list(venue_data.keys()),
                "coverage": {venue: data['coverage_percentage']/100.0 for venue, data in coverage_data.items()}
            }
            
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=f"{s3_path}/OVERLAP.json",
                Body=json.dumps(overlap_data, cls=PandasJSONEncoder, indent=2),
                ContentType='application/json'
            )
            
            # Write tick data for each venue
            for venue, df in venue_data.items():
                if len(df) > 0:
                    parquet_data = df.to_parquet(compression='snappy')
                    self.s3_client.put_object(
                        Bucket=self.bucket,
                        Key=f"{s3_path}/ticks/{venue}/part-0000.parquet",
                        Body=parquet_data,
                        ContentType='application/octet-stream'
                    )
            
            # Write coverage data
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=f"{s3_path}/meta/coverage.json",
                Body=json.dumps(coverage_data, cls=PandasJSONEncoder, indent=2),
                ContentType='application/json'
            )
            
            # Write provenance
            provenance_data = {
                "provenance": "REAL",
                "capture_method": "websocket",
                "code_version": "acdm-dev",
                "commit": "dev",
                "capture_time": datetime.utcnow().isoformat() + "Z"
            }
            
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=f"{s3_path}/meta/provenance.json",
                Body=json.dumps(provenance_data, cls=PandasJSONEncoder, indent=2),
                ContentType='application/json'
            )
            
            logger.info(f"Successfully wrote WebSocket capture to s3://{self.bucket}/{s3_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write to S3: {e}")
            return False

async def main():
    """Main function for WebSocket capture."""
    parser = argparse.ArgumentParser(description="WebSocket market data capture")
    parser.add_argument("--symbol", required=True, help="Trading symbol (e.g., BTC-USD)")
    parser.add_argument("--start", required=True, help="Start time (ISO format)")
    parser.add_argument("--end", required=True, help="End time (ISO format)")
    parser.add_argument("--venues", default="binance,coinbase,kraken,okx,bybit",
                       help="Comma-separated list of venues")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket")
    parser.add_argument("--prefix", default="snapshots", help="S3 prefix")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    try:
        # Parse times
        start_time = datetime.fromisoformat(args.start.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(args.end.replace('Z', '+00:00'))
        
        # Parse venues
        venues = [v.strip() for v in args.venues.split(',')]
        
        # Create capture instance
        capture = WebSocketCapture(args.symbol, venues, args.bucket, args.prefix)
        
        # Capture window
        result = await capture.capture_window(start_time, end_time)
        
        if result["success"]:
            logger.info("WebSocket capture completed successfully")
            print(f"Coverage summary:")
            for venue, data in result["coverage_data"].items():
                print(f"  {venue}: {data['coverage_percentage']:.1f}% ({data['messages_received']} messages)")
            print(f"High coverage venues: {result['high_coverage_venues']}")
            sys.exit(0)
        else:
            logger.error(f"WebSocket capture failed: {result.get('reason', 'unknown')}")
            if 'coverage_data' in result:
                print("Coverage details:")
                for venue, data in result["coverage_data"].items():
                    print(f"  {venue}: {data['coverage_percentage']:.1f}%")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"WebSocket capture failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
