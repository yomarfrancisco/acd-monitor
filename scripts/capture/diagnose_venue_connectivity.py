#!/usr/bin/env python3
"""
Diagnose venue connectivity issues for ETH-USD
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

# Import WebSocket capture
sys.path.append(str(Path(__file__).parent))
from websocket_capture import VenueWebSocket

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def test_venue_connection(venue: str, symbol: str) -> dict:
    """Test connection to a specific venue."""
    logger.info(f"Testing {venue} connection for {symbol}")
    
    try:
        # Create venue WebSocket
        venue_ws = VenueWebSocket(venue, symbol)
        
        # Test connection
        success = await venue_ws.connect()
        
        if success:
            logger.info(f"✅ {venue} connection successful")
            
            # Test subscription
            try:
                # Wait a bit for subscription to be processed
                await asyncio.sleep(2)
                
                # Try to receive a message
                message = await asyncio.wait_for(venue_ws.connection.recv(), timeout=5.0)
                logger.info(f"✅ {venue} received message: {message[:100]}...")
                
                # Close connection
                await venue_ws.connection.close()
                
                return {
                    "venue": venue,
                    "success": True,
                    "message": "Connection and subscription successful"
                }
                
            except asyncio.TimeoutError:
                logger.warning(f"⚠️  {venue} connected but no messages received")
                await venue_ws.connection.close()
                return {
                    "venue": venue,
                    "success": False,
                    "message": "Connected but no messages received"
                }
            except Exception as e:
                logger.error(f"❌ {venue} subscription failed: {e}")
                await venue_ws.connection.close()
                return {
                    "venue": venue,
                    "success": False,
                    "message": f"Subscription failed: {e}"
                }
        else:
            logger.error(f"❌ {venue} connection failed")
            return {
                "venue": venue,
                "success": False,
                "message": "Connection failed"
            }
            
    except Exception as e:
        logger.error(f"❌ {venue} test failed: {e}")
        return {
            "venue": venue,
            "success": False,
            "message": f"Test failed: {e}"
        }

async def main():
    """Test all venues for both symbols."""
    symbols = ["BTC-USD", "ETH-USD"]
    venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
    
    results = {}
    
    for symbol in symbols:
        logger.info(f"\n🔍 Testing {symbol}...")
        results[symbol] = {}
        
        for venue in venues:
            result = await test_venue_connection(venue, symbol)
            results[symbol][venue] = result
            
        # Summary for this symbol
        successful = [v for v, r in results[symbol].items() if r["success"]]
        failed = [v for v, r in results[symbol].items() if not r["success"]]
        
        logger.info(f"\n📊 {symbol} Summary:")
        logger.info(f"  ✅ Successful: {successful}")
        logger.info(f"  ❌ Failed: {failed}")
        
        if len(successful) < 3:
            logger.warning(f"  ⚠️  Only {len(successful)}/5 venues working (need ≥3)")
        else:
            logger.info(f"  ✅ {len(successful)}/5 venues working (sufficient)")
    
    # Overall summary
    logger.info(f"\n📈 Overall Summary:")
    for symbol in symbols:
        successful = [v for v, r in results[symbol].items() if r["success"]]
        logger.info(f"  {symbol}: {len(successful)}/5 venues working")
    
    # Write results to file
    with open("venue_connectivity_test.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"\n📄 Results written to venue_connectivity_test.json")

if __name__ == "__main__":
    asyncio.run(main())
