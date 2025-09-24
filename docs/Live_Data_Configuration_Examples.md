# Live Data Configuration Examples

**Project**: Algorithmic Coordination Diagnostic (ACD) - Phase 4: Regulatory Pilot Deployment  
**Date**: September 21, 2025  
**Version**: 1.0  
**Prepared by**: Theo (AI Assistant)  

---

## 1. Overview

This document provides comprehensive examples of live data configuration for the ACD system, including setup procedures, configuration examples, and operational procedures for various data providers and scenarios.

---

## 2. Data Provider Configuration

### 2.1 Binance Configuration

#### **API Setup**
```yaml
# config/data_providers/binance.yaml
binance:
  api_key: "${BINANCE_API_KEY}"
  secret_key: "${BINANCE_SECRET_KEY}"
  base_url: "https://api.binance.com"
  testnet_url: "https://testnet.binance.vision"
  rate_limit: 1200
  timeout: 30
  retry_attempts: 3
  retry_delay: 1
  
  endpoints:
    order_book: "/api/v3/depth"
    trades: "/api/v3/trades"
    ticker: "/api/v3/ticker/bookTicker"
    klines: "/api/v3/klines"
    exchange_info: "/api/v3/exchangeInfo"
  
  data_types:
    - "order_book"
    - "trades"
    - "ticker"
    - "klines"
  
  symbols:
    - "BTCUSDT"
    - "ETHUSDT"
    - "ADAUSDT"
    - "SOLUSDT"
    - "DOTUSDT"
  
  limits:
    order_book: 5000
    trades: 1000
    klines: 1000
```

#### **Environment Variables**
```bash
# .env
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_key_here
BINANCE_TESTNET=false
BINANCE_RATE_LIMIT=1200
BINANCE_TIMEOUT=30
```

#### **Python Configuration**
```python
# src/acd/data/providers/binance.py
import os
from typing import Dict, List, Optional
import requests
import time

class BinanceProvider:
    def __init__(self, config: Dict[str, Any]):
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.secret_key = os.getenv('BINANCE_SECRET_KEY')
        self.base_url = config.get('base_url', 'https://api.binance.com')
        self.rate_limit = config.get('rate_limit', 1200)
        self.timeout = config.get('timeout', 30)
        self.retry_attempts = config.get('retry_attempts', 3)
        
        self.session = requests.Session()
        self.session.headers.update({
            'X-MBX-APIKEY': self.api_key
        })
        
        self.rate_limiter = RateLimiter(self.rate_limit)
    
    def get_order_book(self, symbol: str, limit: int = 5000) -> Dict:
        """Get order book data"""
        endpoint = f"{self.base_url}/api/v3/depth"
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        return self._make_request(endpoint, params)
    
    def get_trades(self, symbol: str, limit: int = 1000) -> List[Dict]:
        """Get recent trades"""
        endpoint = f"{self.base_url}/api/v3/trades"
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        return self._make_request(endpoint, params)
    
    def get_ticker(self, symbol: str) -> Dict:
        """Get ticker data"""
        endpoint = f"{self.base_url}/api/v3/ticker/bookTicker"
        params = {
            'symbol': symbol
        }
        
        return self._make_request(endpoint, params)
    
    def _make_request(self, endpoint: str, params: Dict) -> Any:
        """Make API request with rate limiting and retry logic"""
        for attempt in range(self.retry_attempts):
            try:
                self.rate_limiter.wait()
                response = self.session.get(endpoint, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == self.retry_attempts - 1:
                    raise
                time.sleep(self.retry_delay * (2 ** attempt))
```

### 2.2 Coinbase Configuration

#### **API Setup**
```yaml
# config/data_providers/coinbase.yaml
coinbase:
  api_key: "${COINBASE_API_KEY}"
  secret_key: "${COINBASE_SECRET_KEY}"
  passphrase: "${COINBASE_PASSPHRASE}"
  base_url: "https://api.exchange.coinbase.com"
  sandbox_url: "https://api-public.sandbox.exchange.coinbase.com"
  rate_limit: 10
  timeout: 30
  retry_attempts: 3
  retry_delay: 1
  
  endpoints:
    order_book: "/products/{product_id}/book"
    trades: "/products/{product_id}/trades"
    ticker: "/products/{product_id}/ticker"
    products: "/products"
    currencies: "/currencies"
  
  data_types:
    - "order_book"
    - "trades"
    - "ticker"
    - "products"
  
  symbols:
    - "BTC-USD"
    - "ETH-USD"
    - "ADA-USD"
    - "SOL-USD"
    - "DOT-USD"
  
  limits:
    order_book: 100
    trades: 100
```

#### **Environment Variables**
```bash
# .env
COINBASE_API_KEY=your_coinbase_api_key_here
COINBASE_SECRET_KEY=your_coinbase_secret_key_here
COINBASE_PASSPHRASE=your_coinbase_passphrase_here
COINBASE_SANDBOX=false
COINBASE_RATE_LIMIT=10
COINBASE_TIMEOUT=30
```

#### **Python Configuration**
```python
# src/acd/data/providers/coinbase.py
import os
import hmac
import hashlib
import base64
import time
from typing import Dict, List, Optional
import requests

class CoinbaseProvider:
    def __init__(self, config: Dict[str, Any]):
        self.api_key = os.getenv('COINBASE_API_KEY')
        self.secret_key = os.getenv('COINBASE_SECRET_KEY')
        self.passphrase = os.getenv('COINBASE_PASSPHRASE')
        self.base_url = config.get('base_url', 'https://api.exchange.coinbase.com')
        self.rate_limit = config.get('rate_limit', 10)
        self.timeout = config.get('timeout', 30)
        self.retry_attempts = config.get('retry_attempts', 3)
        
        self.session = requests.Session()
        self.rate_limiter = RateLimiter(self.rate_limit)
    
    def _generate_signature(self, timestamp: str, method: str, path: str, body: str = '') -> str:
        """Generate Coinbase signature"""
        message = timestamp + method + path + body
        signature = hmac.new(
            base64.b64decode(self.secret_key),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode('utf-8')
    
    def _get_headers(self, method: str, path: str, body: str = '') -> Dict[str, str]:
        """Get request headers with authentication"""
        timestamp = str(time.time())
        signature = self._generate_signature(timestamp, method, path, body)
        
        return {
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-SIGN': signature,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
    
    def get_order_book(self, product_id: str, level: int = 2) -> Dict:
        """Get order book data"""
        endpoint = f"{self.base_url}/products/{product_id}/book"
        params = {'level': level}
        
        headers = self._get_headers('GET', f"/products/{product_id}/book")
        return self._make_request(endpoint, params, headers)
    
    def get_trades(self, product_id: str, limit: int = 100) -> List[Dict]:
        """Get recent trades"""
        endpoint = f"{self.base_url}/products/{product_id}/trades"
        params = {'limit': limit}
        
        headers = self._get_headers('GET', f"/products/{product_id}/trades")
        return self._make_request(endpoint, params, headers)
    
    def get_ticker(self, product_id: str) -> Dict:
        """Get ticker data"""
        endpoint = f"{self.base_url}/products/{product_id}/ticker"
        
        headers = self._get_headers('GET', f"/products/{product_id}/ticker")
        return self._make_request(endpoint, {}, headers)
    
    def _make_request(self, endpoint: str, params: Dict, headers: Dict) -> Any:
        """Make API request with rate limiting and retry logic"""
        for attempt in range(self.retry_attempts):
            try:
                self.rate_limiter.wait()
                response = self.session.get(
                    endpoint, 
                    params=params, 
                    headers=headers, 
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == self.retry_attempts - 1:
                    raise
                time.sleep(self.retry_delay * (2 ** attempt))
```

### 2.3 Kraken Configuration

#### **API Setup**
```yaml
# config/data_providers/kraken.yaml
kraken:
  api_key: "${KRAKEN_API_KEY}"
  secret_key: "${KRAKEN_SECRET_KEY}"
  base_url: "https://api.kraken.com"
  rate_limit: 1
  timeout: 30
  retry_attempts: 3
  retry_delay: 1
  
  endpoints:
    order_book: "/0/public/Depth"
    trades: "/0/public/Trades"
    ticker: "/0/public/Ticker"
    assets: "/0/public/Assets"
    asset_pairs: "/0/public/AssetPairs"
  
  data_types:
    - "order_book"
    - "trades"
    - "ticker"
    - "assets"
  
  symbols:
    - "XXBTZUSD"
    - "XETHZUSD"
    - "ADAUSD"
    - "SOLUSD"
    - "DOTUSD"
  
  limits:
    order_book: 1000
    trades: 1000
```

#### **Environment Variables**
```bash
# .env
KRAKEN_API_KEY=your_kraken_api_key_here
KRAKEN_SECRET_KEY=your_kraken_secret_key_here
KRAKEN_RATE_LIMIT=1
KRAKEN_TIMEOUT=30
```

#### **Python Configuration**
```python
# src/acd/data/providers/kraken.py
import os
import urllib.parse
import hmac
import hashlib
import base64
import time
from typing import Dict, List, Optional
import requests

class KrakenProvider:
    def __init__(self, config: Dict[str, Any]):
        self.api_key = os.getenv('KRAKEN_API_KEY')
        self.secret_key = os.getenv('KRAKEN_SECRET_KEY')
        self.base_url = config.get('base_url', 'https://api.kraken.com')
        self.rate_limit = config.get('rate_limit', 1)
        self.timeout = config.get('timeout', 30)
        self.retry_attempts = config.get('retry_attempts', 3)
        
        self.session = requests.Session()
        self.rate_limiter = RateLimiter(self.rate_limit)
    
    def _generate_signature(self, path: str, data: Dict, nonce: str) -> str:
        """Generate Kraken signature"""
        postdata = urllib.parse.urlencode(data)
        encoded = (nonce + postdata).encode()
        message = path.encode() + hashlib.sha256(encoded).digest()
        
        signature = hmac.new(
            base64.b64decode(self.secret_key),
            message,
            hashlib.sha512
        )
        return base64.b64encode(signature.digest()).decode()
    
    def _get_headers(self, path: str, data: Dict) -> Dict[str, str]:
        """Get request headers with authentication"""
        nonce = str(int(time.time() * 1000))
        data['nonce'] = nonce
        signature = self._generate_signature(path, data, nonce)
        
        return {
            'API-Key': self.api_key,
            'API-Sign': signature
        }
    
    def get_order_book(self, pair: str, count: int = 1000) -> Dict:
        """Get order book data"""
        endpoint = f"{self.base_url}/0/public/Depth"
        data = {
            'pair': pair,
            'count': count
        }
        
        headers = self._get_headers('/0/public/Depth', data)
        return self._make_request(endpoint, data, headers)
    
    def get_trades(self, pair: str, count: int = 1000) -> Dict:
        """Get recent trades"""
        endpoint = f"{self.base_url}/0/public/Trades"
        data = {
            'pair': pair,
            'count': count
        }
        
        headers = self._get_headers('/0/public/Trades', data)
        return self._make_request(endpoint, data, headers)
    
    def get_ticker(self, pair: str) -> Dict:
        """Get ticker data"""
        endpoint = f"{self.base_url}/0/public/Ticker"
        data = {'pair': pair}
        
        headers = self._get_headers('/0/public/Ticker', data)
        return self._make_request(endpoint, data, headers)
    
    def _make_request(self, endpoint: str, data: Dict, headers: Dict) -> Any:
        """Make API request with rate limiting and retry logic"""
        for attempt in range(self.retry_attempts):
            try:
                self.rate_limiter.wait()
                response = self.session.post(
                    endpoint,
                    data=data,
                    headers=headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == self.retry_attempts - 1:
                    raise
                time.sleep(self.retry_delay * (2 ** attempt))
```

---

## 3. Data Collection Configuration

### 3.1 Real-time Data Collection

#### **Collection Configuration**
```yaml
# config/data_collection.yaml
data_collection:
  mode: "real_time"  # or "batch", "hybrid"
  interval: 1  # seconds
  batch_size: 1000
  max_workers: 4
  timeout: 30
  retry_attempts: 3
  
  sources:
    - name: "binance"
      enabled: true
      symbols: ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
      data_types: ["order_book", "trades", "ticker"]
      rate_limit: 1200
    
    - name: "coinbase"
      enabled: true
      symbols: ["BTC-USD", "ETH-USD", "ADA-USD"]
      data_types: ["order_book", "trades", "ticker"]
      rate_limit: 10
    
    - name: "kraken"
      enabled: true
      symbols: ["XXBTZUSD", "XETHZUSD", "ADAUSD"]
      data_types: ["order_book", "trades", "ticker"]
      rate_limit: 1
  
  storage:
    type: "database"  # or "file", "hybrid"
    database:
      host: "localhost"
      port: 5432
      name: "acd_data"
      user: "acd_user"
      password: "${DB_PASSWORD}"
    
    file:
      path: "/opt/acd-data"
      format: "parquet"
      compression: "snappy"
      partition_by: ["exchange", "symbol", "date"]
  
  processing:
    chunk_size: 1000
    max_workers: 4
    timeout: 30
    retry_attempts: 3
    validation: true
    cleaning: true
    normalization: true
```

#### **Collection Script**
```python
# scripts/setup_live_data_collection.py
import asyncio
import aiohttp
from typing import Dict, List, Any
from src.acd.data import LiveDataCollector

async def setup_live_data_collection():
    """Setup live data collection for pilot"""
    
    collector = LiveDataCollector()
    
    # Configure data sources
    sources = [
        {
            'name': 'binance',
            'symbols': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT'],
            'data_types': ['order_book', 'trades', 'ticker'],
            'rate_limit': 1200
        },
        {
            'name': 'coinbase',
            'symbols': ['BTC-USD', 'ETH-USD', 'ADA-USD'],
            'data_types': ['order_book', 'trades', 'ticker'],
            'rate_limit': 10
        },
        {
            'name': 'kraken',
            'symbols': ['XXBTZUSD', 'XETHZUSD', 'ADAUSD'],
            'data_types': ['order_book', 'trades', 'ticker'],
            'rate_limit': 1
        }
    ]
    
    # Start data collection
    tasks = []
    for source in sources:
        task = asyncio.create_task(
            collector.start_collection(
                exchange=source['name'],
                symbols=source['symbols'],
                data_types=source['data_types'],
                rate_limit=source['rate_limit']
            )
        )
        tasks.append(task)
    
    # Wait for all collection tasks
    await asyncio.gather(*tasks)
    
    return collector

if __name__ == "__main__":
    asyncio.run(setup_live_data_collection())
```

### 3.2 Batch Data Collection

#### **Batch Configuration**
```yaml
# config/batch_collection.yaml
batch_collection:
  mode: "batch"
  schedule: "0 */6 * * *"  # Every 6 hours
  batch_size: 10000
  max_workers: 8
  timeout: 300
  retry_attempts: 3
  
  sources:
    - name: "binance"
      enabled: true
      symbols: ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
      data_types: ["klines"]
      interval: "1m"
      limit: 1000
    
    - name: "coinbase"
      enabled: true
      symbols: ["BTC-USD", "ETH-USD", "ADA-USD"]
      data_types: ["candles"]
      granularity: 60
      limit: 300
    
    - name: "kraken"
      enabled: true
      symbols: ["XXBTZUSD", "XETHZUSD", "ADAUSD"]
      data_types: ["ohlc"]
      interval: 1
      limit: 1000
  
  storage:
    type: "database"
    database:
      host: "localhost"
      port: 5432
      name: "acd_data"
      user: "acd_user"
      password: "${DB_PASSWORD}"
    
    file:
      path: "/opt/acd-data/batch"
      format: "parquet"
      compression: "snappy"
      partition_by: ["exchange", "symbol", "date"]
```

#### **Batch Collection Script**
```python
# scripts/setup_batch_data_collection.py
import schedule
import time
from typing import Dict, List, Any
from src.acd.data import BatchDataCollector

def setup_batch_data_collection():
    """Setup batch data collection for pilot"""
    
    collector = BatchDataCollector()
    
    # Configure batch collection
    config = {
        'sources': [
            {
                'name': 'binance',
                'symbols': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT'],
                'data_types': ['klines'],
                'interval': '1m',
                'limit': 1000
            },
            {
                'name': 'coinbase',
                'symbols': ['BTC-USD', 'ETH-USD', 'ADA-USD'],
                'data_types': ['candles'],
                'granularity': 60,
                'limit': 300
            },
            {
                'name': 'kraken',
                'symbols': ['XXBTZUSD', 'XETHZUSD', 'ADAUSD'],
                'data_types': ['ohlc'],
                'interval': 1,
                'limit': 1000
            }
        ],
        'storage': {
            'type': 'database',
            'database': {
                'host': 'localhost',
                'port': 5432,
                'name': 'acd_data',
                'user': 'acd_user',
                'password': os.getenv('DB_PASSWORD')
            }
        }
    }
    
    # Schedule batch collection
    schedule.every(6).hours.do(collector.collect_batch_data, config)
    
    # Start scheduler
    while True:
        schedule.run_pending()
        time.sleep(60)
    
    return collector

if __name__ == "__main__":
    setup_batch_data_collection()
```

---

## 4. Data Processing Configuration

### 4.1 Real-time Processing

#### **Processing Configuration**
```yaml
# config/data_processing.yaml
data_processing:
  mode: "real_time"
  pipeline:
    - name: "data_validation"
      enabled: true
      config:
        validate_schema: true
        validate_range: true
        validate_consistency: true
    
    - name: "data_cleaning"
      enabled: true
      config:
        remove_duplicates: true
        fill_missing_values: true
        outlier_detection: true
        outlier_threshold: 3.0
    
    - name: "data_normalization"
      enabled: true
      config:
        normalize_prices: true
        normalize_volumes: true
        standardize_timestamps: true
        timezone: "UTC"
    
    - name: "data_aggregation"
      enabled: true
      config:
        aggregate_by: "1m"
        aggregation_methods: ["mean", "sum", "count"]
        preserve_original: true
  
  storage:
    type: "database"
    database:
      host: "localhost"
      port: 5432
      name: "acd_processed"
      user: "acd_user"
      password: "${DB_PASSWORD}"
    
    file:
      path: "/opt/acd-data/processed"
      format: "parquet"
      compression: "snappy"
      partition_by: ["exchange", "symbol", "date"]
  
  monitoring:
    enabled: true
    metrics:
      - "processing_latency"
      - "data_quality"
      - "error_rate"
      - "throughput"
    alerts:
      - "high_latency"
      - "low_quality"
      - "high_error_rate"
      - "low_throughput"
```

#### **Processing Script**
```python
# scripts/setup_data_processing.py
import asyncio
from typing import Dict, List, Any
from src.acd.data import DataProcessor

async def setup_data_processing():
    """Setup data processing pipeline for pilot"""
    
    processor = DataProcessor()
    
    # Configure processing pipeline
    pipeline_config = {
        'data_validation': {
            'enabled': True,
            'config': {
                'validate_schema': True,
                'validate_range': True,
                'validate_consistency': True
            }
        },
        'data_cleaning': {
            'enabled': True,
            'config': {
                'remove_duplicates': True,
                'fill_missing_values': True,
                'outlier_detection': True,
                'outlier_threshold': 3.0
            }
        },
        'data_normalization': {
            'enabled': True,
            'config': {
                'normalize_prices': True,
                'normalize_volumes': True,
                'standardize_timestamps': True,
                'timezone': 'UTC'
            }
        },
        'data_aggregation': {
            'enabled': True,
            'config': {
                'aggregate_by': '1m',
                'aggregation_methods': ['mean', 'sum', 'count'],
                'preserve_original': True
            }
        }
    }
    
    # Setup processing pipeline
    await processor.setup_pipeline(pipeline_config)
    
    # Start processing
    await processor.start_processing()
    
    return processor

if __name__ == "__main__":
    asyncio.run(setup_data_processing())
```

### 4.2 Batch Processing

#### **Batch Processing Configuration**
```yaml
# config/batch_processing.yaml
batch_processing:
  mode: "batch"
  schedule: "0 1 * * *"  # Daily at 1 AM
  batch_size: 100000
  max_workers: 8
  timeout: 3600
  retry_attempts: 3
  
  pipeline:
    - name: "data_validation"
      enabled: true
      config:
        validate_schema: true
        validate_range: true
        validate_consistency: true
    
    - name: "data_cleaning"
      enabled: true
      config:
        remove_duplicates: true
        fill_missing_values: true
        outlier_detection: true
        outlier_threshold: 3.0
    
    - name: "data_normalization"
      enabled: true
      config:
        normalize_prices: true
        normalize_volumes: true
        standardize_timestamps: true
        timezone: "UTC"
    
    - name: "data_aggregation"
      enabled: true
      config:
        aggregate_by: "1h"
        aggregation_methods: ["mean", "sum", "count", "min", "max"]
        preserve_original: true
    
    - name: "feature_engineering"
      enabled: true
      config:
        technical_indicators: true
        price_features: true
        volume_features: true
        volatility_features: true
  
  storage:
    type: "database"
    database:
      host: "localhost"
      port: 5432
      name: "acd_processed"
      user: "acd_user"
      password: "${DB_PASSWORD}"
    
    file:
      path: "/opt/acd-data/processed/batch"
      format: "parquet"
      compression: "snappy"
      partition_by: ["exchange", "symbol", "date"]
```

---

## 5. Data Quality Configuration

### 5.1 Quality Monitoring

#### **Quality Configuration**
```yaml
# config/data_quality.yaml
data_quality:
  monitoring:
    enabled: true
    interval: 300  # 5 minutes
    thresholds:
      completeness: 0.95
      accuracy: 0.99
      consistency: 0.98
      timeliness: 60  # seconds
  
  validation:
    schema_validation: true
    range_validation: true
    consistency_validation: true
    cross_source_validation: true
  
  cleaning:
    remove_duplicates: true
    fill_missing_values: true
    outlier_detection: true
    outlier_threshold: 3.0
  
  reporting:
    enabled: true
    format: "json"
    destination: "/opt/acd-data/quality-reports"
    retention_days: 30
  
  alerts:
    enabled: true
    channels:
      - "email"
      - "slack"
      - "webhook"
    thresholds:
      completeness: 0.90
      accuracy: 0.95
      consistency: 0.90
      timeliness: 120
```

#### **Quality Monitoring Script**
```python
# scripts/setup_data_quality_monitoring.py
import schedule
import time
from typing import Dict, List, Any
from src.acd.data import DataQualityMonitor

def setup_data_quality_monitoring():
    """Setup data quality monitoring for pilot"""
    
    monitor = DataQualityMonitor()
    
    # Configure quality monitoring
    config = {
        'monitoring': {
            'enabled': True,
            'interval': 300,  # 5 minutes
            'thresholds': {
                'completeness': 0.95,
                'accuracy': 0.99,
                'consistency': 0.98,
                'timeliness': 60
            }
        },
        'validation': {
            'schema_validation': True,
            'range_validation': True,
            'consistency_validation': True,
            'cross_source_validation': True
        },
        'cleaning': {
            'remove_duplicates': True,
            'fill_missing_values': True,
            'outlier_detection': True,
            'outlier_threshold': 3.0
        },
        'reporting': {
            'enabled': True,
            'format': 'json',
            'destination': '/opt/acd-data/quality-reports',
            'retention_days': 30
        },
        'alerts': {
            'enabled': True,
            'channels': ['email', 'slack', 'webhook'],
            'thresholds': {
                'completeness': 0.90,
                'accuracy': 0.95,
                'consistency': 0.90,
                'timeliness': 120
            }
        }
    }
    
    # Setup quality monitoring
    monitor.setup_monitoring(config)
    
    # Schedule quality checks
    schedule.every(5).minutes.do(monitor.check_data_quality)
    schedule.every().hour.do(monitor.generate_quality_report)
    schedule.every().day.at("00:00").do(monitor.generate_daily_quality_report)
    
    # Start monitoring
    while True:
        schedule.run_pending()
        time.sleep(60)
    
    return monitor

if __name__ == "__main__":
    setup_data_quality_monitoring()
```

---

## 6. Data Storage Configuration

### 6.1 Database Configuration

#### **PostgreSQL Configuration**
```yaml
# config/database/postgresql.yaml
database:
  type: "postgresql"
  host: "localhost"
  port: 5432
  name: "acd_data"
  user: "acd_user"
  password: "${DB_PASSWORD}"
  ssl_mode: "prefer"
  pool_size: 20
  max_overflow: 30
  pool_timeout: 30
  pool_recycle: 3600
  
  tables:
    market_data:
      schema: "public"
      table: "market_data"
      indexes:
        - ["exchange", "symbol", "timestamp"]
        - ["symbol", "timestamp"]
        - ["timestamp"]
    
    processed_data:
      schema: "public"
      table: "processed_data"
      indexes:
        - ["exchange", "symbol", "timestamp"]
        - ["symbol", "timestamp"]
        - ["timestamp"]
    
    quality_metrics:
      schema: "public"
      table: "quality_metrics"
      indexes:
        - ["exchange", "symbol", "timestamp"]
        - ["timestamp"]
  
  backup:
    enabled: true
    schedule: "0 2 * * *"  # Daily at 2 AM
    retention_days: 30
    destination: "/opt/acd-backups"
```

#### **Database Setup Script**
```python
# scripts/setup_database.py
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from typing import Dict, List, Any

def setup_database():
    """Setup database for pilot"""
    
    # Database configuration
    config = {
        'host': 'localhost',
        'port': 5432,
        'name': 'acd_data',
        'user': 'acd_user',
        'password': os.getenv('DB_PASSWORD')
    }
    
    # Connect to PostgreSQL
    conn = psycopg2.connect(
        host=config['host'],
        port=config['port'],
        user=config['user'],
        password=config['password'],
        database='postgres'
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    cursor = conn.cursor()
    
    # Create database
    cursor.execute(f"CREATE DATABASE {config['name']}")
    
    # Create user
    cursor.execute(f"CREATE USER {config['user']} WITH PASSWORD '{config['password']}'")
    cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {config['name']} TO {config['user']}")
    
    cursor.close()
    conn.close()
    
    # Connect to new database
    conn = psycopg2.connect(
        host=config['host'],
        port=config['port'],
        user=config['user'],
        password=config['password'],
        database=config['name']
    )
    
    cursor = conn.cursor()
    
    # Create tables
    create_tables(cursor)
    
    # Create indexes
    create_indexes(cursor)
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return config

def create_tables(cursor):
    """Create database tables"""
    
    # Market data table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            id SERIAL PRIMARY KEY,
            exchange VARCHAR(50) NOT NULL,
            symbol VARCHAR(50) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            data_type VARCHAR(50) NOT NULL,
            data JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Processed data table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed_data (
            id SERIAL PRIMARY KEY,
            exchange VARCHAR(50) NOT NULL,
            symbol VARCHAR(50) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            data_type VARCHAR(50) NOT NULL,
            data JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Quality metrics table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quality_metrics (
            id SERIAL PRIMARY KEY,
            exchange VARCHAR(50) NOT NULL,
            symbol VARCHAR(50) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            completeness FLOAT,
            accuracy FLOAT,
            consistency FLOAT,
            timeliness FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

def create_indexes(cursor):
    """Create database indexes"""
    
    # Market data indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_data_exchange_symbol_timestamp ON market_data (exchange, symbol, timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timestamp ON market_data (symbol, timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data (timestamp)")
    
    # Processed data indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_processed_data_exchange_symbol_timestamp ON processed_data (exchange, symbol, timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_processed_data_symbol_timestamp ON processed_data (symbol, timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_processed_data_timestamp ON processed_data (timestamp)")
    
    # Quality metrics indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality_metrics_exchange_symbol_timestamp ON quality_metrics (exchange, symbol, timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality_metrics_timestamp ON quality_metrics (timestamp)")

if __name__ == "__main__":
    setup_database()
```

### 6.2 File Storage Configuration

#### **File Storage Configuration**
```yaml
# config/file_storage.yaml
file_storage:
  type: "local"  # or "s3", "gcs", "azure"
  base_path: "/opt/acd-data"
  
  structure:
    raw_data: "raw/{exchange}/{symbol}/{date}"
    processed_data: "processed/{exchange}/{symbol}/{date}"
    quality_reports: "quality/{date}"
    backups: "backups/{date}"
  
  formats:
    raw_data: "json"
    processed_data: "parquet"
    quality_reports: "json"
    backups: "tar.gz"
  
  compression:
    raw_data: "gzip"
    processed_data: "snappy"
    quality_reports: "gzip"
    backups: "gzip"
  
  retention:
    raw_data: 90  # days
    processed_data: 365  # days
    quality_reports: 30  # days
    backups: 30  # days
  
  partitioning:
    enabled: true
    partition_by: ["exchange", "symbol", "date"]
    partition_format: "YYYY-MM-DD"
```

---

## 7. Conclusion

This document provides comprehensive examples of live data configuration for the ACD system, including setup procedures, configuration examples, and operational procedures for various data providers and scenarios.

For additional support or questions, please refer to the troubleshooting section or contact the technical support team.

---

**Document Status**: COMPLETED - Version 1.0  
**Prepared by**: Theo (AI Assistant)  
**Date**: September 21, 2025  
**Next Review**: End of Week 4



