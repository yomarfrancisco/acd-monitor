# ACD Deployment Guide

**Project**: Algorithmic Coordination Diagnostic (ACD) - Phase 4: Regulatory Pilot Deployment  
**Date**: September 21, 2025  
**Version**: 1.0  
**Prepared by**: Theo (AI Assistant)  

---

## 1. Executive Summary

This deployment guide provides comprehensive instructions for deploying the ACD system in both offline and live environments. The guide covers system requirements, installation procedures, configuration, testing, and operational procedures.

---

## 2. System Requirements

### 2.1 Hardware Requirements

#### **Minimum Requirements**
- **CPU**: 4 cores, 2.4 GHz
- **RAM**: 8 GB
- **Storage**: 50 GB available space
- **Network**: 100 Mbps internet connection

#### **Recommended Requirements**
- **CPU**: 8 cores, 3.0 GHz
- **RAM**: 16 GB
- **Storage**: 100 GB SSD
- **Network**: 1 Gbps internet connection

#### **Production Requirements**
- **CPU**: 16 cores, 3.5 GHz
- **RAM**: 32 GB
- **Storage**: 500 GB NVMe SSD
- **Network**: 10 Gbps internet connection

### 2.2 Software Requirements

#### **Operating System**
- **Linux**: Ubuntu 20.04 LTS or later, CentOS 8 or later
- **macOS**: macOS 10.15 or later
- **Windows**: Windows 10 or later (with WSL2 recommended)

#### **Python Environment**
- **Python**: 3.9 or later
- **pip**: Latest version
- **virtualenv**: For environment isolation

#### **Dependencies**
- **NumPy**: 1.21.0 or later
- **Pandas**: 1.3.0 or later
- **SciPy**: 1.7.0 or later
- **Scikit-learn**: 1.0.0 or later
- **Matplotlib**: 3.4.0 or later
- **Seaborn**: 0.11.0 or later

### 2.3 External Services

#### **Required Services**
- **Chatbase API**: For live conversational interface (optional)
- **Crypto Data Feeds**: For live market data (optional)
- **File Storage**: Local or cloud storage for artifacts

#### **Optional Services**
- **Database**: PostgreSQL or MongoDB for data persistence
- **Message Queue**: Redis or RabbitMQ for task queuing
- **Monitoring**: Prometheus, Grafana for system monitoring

---

## 3. Installation Procedures

### 3.1 Environment Setup

#### **Step 1: Create Virtual Environment**
```bash
# Create virtual environment
python -m venv acd-env

# Activate virtual environment
# On Linux/macOS:
source acd-env/bin/activate
# On Windows:
acd-env\Scripts\activate
```

#### **Step 2: Install Dependencies**
```bash
# Install core dependencies
pip install numpy pandas scipy scikit-learn matplotlib seaborn

# Install additional dependencies
pip install requests python-dotenv pydantic dataclasses-json

# Install development dependencies (optional)
pip install pytest black flake8 mypy
```

#### **Step 3: Clone Repository**
```bash
# Clone the repository
git clone <repository-url>
cd acd-monitor

# Install the package in development mode
pip install -e .
```

### 3.2 Configuration Setup

#### **Step 1: Environment Variables**
Create a `.env` file in the project root:

```bash
# Chatbase Configuration (optional)
CHATBASE_API_KEY=your_chatbase_api_key
CHATBASE_ASSISTANT_ID=your_assistant_id
CHATBASE_USE_LEGACY=true

# Data Configuration
DATA_DIR=./data
ARTIFACTS_DIR=./artifacts
LOGS_DIR=./logs

# Analysis Configuration
DEFAULT_SEED=42
MAX_SAMPLES=10000
CONFIDENCE_LEVEL=0.95

# Performance Configuration
MAX_WORKERS=4
CHUNK_SIZE=1000
TIMEOUT_SECONDS=30
```

#### **Step 2: Directory Structure**
```bash
# Create required directories
mkdir -p data artifacts logs reports

# Set permissions
chmod 755 data artifacts logs reports
```

#### **Step 3: Configuration Files**
Create configuration files:

```bash
# Create main configuration file
cp config/config.example.yaml config/config.yaml

# Edit configuration as needed
nano config/config.yaml
```

### 3.3 System Validation

#### **Step 1: Run System Tests**
```bash
# Run unit tests
python -m pytest tests/ -v

# Run integration tests
python -m pytest tests/integration/ -v

# Run system validation
python scripts/validate_system.py
```

#### **Step 2: Verify Dependencies**
```bash
# Check Python version
python --version

# Check installed packages
pip list

# Verify system requirements
python scripts/check_requirements.py
```

---

## 4. Configuration

### 4.1 Core Configuration

#### **Analysis Configuration**
```yaml
# config/config.yaml
analysis:
  icp:
    significance_level: 0.05
    bootstrap_samples: 1000
    min_samples_per_env: 100
    power_threshold: 0.8
  
  vmm:
    convergence_tolerance: 1e-6
    max_iterations: 1000
    regularization: 0.01
  
  validation:
    lead_lag:
      window_size: 30
      min_observations: 50
    mirroring:
      similarity_threshold: 0.7
      min_observations: 50
    hmm:
      n_states: 3
      max_iterations: 100
    infoflow:
      transfer_entropy_threshold: 0.1
```

#### **Data Configuration**
```yaml
data:
  sources:
    - name: "binance"
      type: "crypto"
      endpoint: "https://api.binance.com"
      rate_limit: 1200
    - name: "coinbase"
      type: "crypto"
      endpoint: "https://api.exchange.coinbase.com"
      rate_limit: 10
    - name: "kraken"
      type: "crypto"
      endpoint: "https://api.kraken.com"
      rate_limit: 1
  
  processing:
    chunk_size: 1000
    max_workers: 4
    timeout: 30
    retry_attempts: 3
```

#### **Output Configuration**
```yaml
output:
  formats:
    - "json"
    - "pdf"
    - "csv"
  
  directories:
    reports: "./artifacts/reports"
    logs: "./logs"
    temp: "./temp"
  
  quality:
    compression: true
    encryption: false
    checksums: true
```

### 4.2 Environment-Specific Configuration

#### **Development Environment**
```yaml
# config/dev.yaml
environment: "development"
debug: true
log_level: "DEBUG"
mock_data: true
live_apis: false
```

#### **Staging Environment**
```yaml
# config/staging.yaml
environment: "staging"
debug: false
log_level: "INFO"
mock_data: false
live_apis: true
rate_limits: 0.5
```

#### **Production Environment**
```yaml
# config/prod.yaml
environment: "production"
debug: false
log_level: "WARNING"
mock_data: false
live_apis: true
rate_limits: 1.0
monitoring: true
```

---

## 5. Deployment Modes

### 5.1 Offline Mode

#### **Configuration**
```bash
# Set offline mode
export ACD_MODE=offline
export MOCK_DATA=true
export LIVE_APIS=false
```

#### **Features**
- **Mock Data**: Uses synthetic data for testing
- **Offline Provider**: Uses offline mock provider for responses
- **No External APIs**: No dependency on external services
- **Full Functionality**: All analysis capabilities available

#### **Use Cases**
- **Development**: Local development and testing
- **Demonstration**: System demonstrations and pilots
- **Training**: User training and onboarding
- **Testing**: Comprehensive testing without external dependencies

### 5.2 Live Mode

#### **Configuration**
```bash
# Set live mode
export ACD_MODE=live
export MOCK_DATA=false
export LIVE_APIS=true
```

#### **Features**
- **Live Data**: Real-time market data feeds
- **Live APIs**: Integration with external services
- **Real-time Analysis**: Live coordination detection
- **Production Ready**: Full production capabilities

#### **Use Cases**
- **Production**: Live regulatory monitoring
- **Pilot Programs**: Real-world pilot deployments
- **Research**: Live market research and analysis
- **Surveillance**: Active market surveillance

### 5.3 Hybrid Mode

#### **Configuration**
```bash
# Set hybrid mode
export ACD_MODE=hybrid
export MOCK_DATA=false
export LIVE_APIS=true
export FALLBACK_MODE=true
```

#### **Features**
- **Live Primary**: Live data and APIs as primary
- **Offline Fallback**: Offline mode as fallback
- **Graceful Degradation**: Automatic fallback on failures
- **High Availability**: Maximum system availability

#### **Use Cases**
- **Production**: Production with fallback capabilities
- **Pilot Programs**: Pilots with reliability guarantees
- **Critical Systems**: Systems requiring high availability
- **Regulatory**: Regulatory systems with uptime requirements

---

## 6. Bundle Generation

### 6.1 Bundle Types

#### **Regulatory Bundles**
- **Executive Summary**: High-level risk assessment
- **Technical Report**: Detailed analysis and methodology
- **Attribution Tables**: Risk decomposition and drivers
- **Provenance Files**: Complete audit trails

#### **Bundle Formats**
- **JSON**: Machine-readable structured data
- **PDF**: Human-readable regulatory documents
- **CSV**: Tabular data for analysis
- **XML**: Structured data for integration

### 6.2 Bundle Generation Process

#### **Step 1: Data Preparation**
```python
# Load and prepare data
from src.acd.data import DataLoader

loader = DataLoader()
data = loader.load_market_data(
    exchanges=['binance', 'coinbase', 'kraken'],
    pairs=['BTC/USD', 'ETH/USD'],
    time_period='last_30_days'
)
```

#### **Step 2: Analysis Execution**
```python
# Run analysis
from src.acd.analytics import IntegratedEngine

engine = IntegratedEngine()
results = engine.run_analysis(data)
```

#### **Step 3: Bundle Generation**
```python
# Generate bundle
from src.acd.analytics.report_v2 import ReportV2Generator

generator = ReportV2Generator()
bundle = generator.generate_bundle(
    results=results,
    bundle_type='regulatory',
    include_attribution=True,
    include_provenance=True
)
```

#### **Step 4: Bundle Export**
```python
# Export bundle
bundle.export(
    output_dir='./artifacts/reports',
    formats=['json', 'pdf'],
    include_attribution=True,
    include_provenance=True
)
```

### 6.3 Bundle Customization

#### **Custom Templates**
```python
# Custom bundle template
template = {
    'executive_summary': True,
    'technical_methodology': True,
    'statistical_results': True,
    'attribution_tables': True,
    'alternative_explanations': True,
    'audit_trail': True
}

bundle = generator.generate_bundle(
    results=results,
    template=template
)
```

#### **Custom Styling**
```python
# Custom styling
styling = {
    'theme': 'regulatory',
    'colors': ['#1f77b4', '#ff7f0e', '#2ca02c'],
    'fonts': {'title': 'Arial', 'body': 'Times New Roman'},
    'logo': './assets/logo.png'
}

bundle = generator.generate_bundle(
    results=results,
    styling=styling
)
```

---

## 7. API Integration

### 7.1 REST API

#### **Endpoints**
```bash
# Health check
GET /api/health

# Analysis endpoints
POST /api/analysis/icp
POST /api/analysis/vmm
POST /api/analysis/validation
POST /api/analysis/integrated

# Bundle endpoints
POST /api/bundles/generate
GET /api/bundles/{bundle_id}
GET /api/bundles/{bundle_id}/download

# Data endpoints
GET /api/data/market
POST /api/data/upload
GET /api/data/status
```

#### **Authentication**
```bash
# API key authentication
curl -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -X POST http://localhost:8000/api/analysis/icp
```

### 7.2 Python SDK

#### **Installation**
```bash
pip install acd-sdk
```

#### **Usage**
```python
from acd_sdk import ACDClient

# Initialize client
client = ACDClient(
    api_key='your_api_key',
    base_url='http://localhost:8000'
)

# Run analysis
results = client.run_analysis(
    exchanges=['binance', 'coinbase'],
    pairs=['BTC/USD', 'ETH/USD'],
    time_period='last_30_days'
)

# Generate bundle
bundle = client.generate_bundle(
    results=results,
    bundle_type='regulatory'
)
```

### 7.3 WebSocket API

#### **Real-time Updates**
```python
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    print(f"Received: {data}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Connection closed")

# Connect to WebSocket
ws = websocket.WebSocketApp(
    "ws://localhost:8000/ws/analysis",
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)

ws.run_forever()
```

---

## 8. Monitoring and Maintenance

### 8.1 System Monitoring

#### **Health Checks**
```bash
# System health check
curl http://localhost:8000/api/health

# Detailed health check
curl http://localhost:8000/api/health/detailed
```

#### **Performance Monitoring**
```python
# Performance metrics
from src.acd.monitoring import PerformanceMonitor

monitor = PerformanceMonitor()
metrics = monitor.get_metrics()

print(f"CPU Usage: {metrics['cpu_usage']}%")
print(f"Memory Usage: {metrics['memory_usage']}%")
print(f"Disk Usage: {metrics['disk_usage']}%")
print(f"Network Usage: {metrics['network_usage']}%")
```

#### **Log Monitoring**
```bash
# View logs
tail -f logs/acd.log

# Search logs
grep "ERROR" logs/acd.log

# Log analysis
python scripts/analyze_logs.py
```

### 8.2 Maintenance Procedures

#### **Daily Maintenance**
```bash
# Check system health
python scripts/health_check.py

# Clean temporary files
python scripts/cleanup.py

# Backup artifacts
python scripts/backup.py
```

#### **Weekly Maintenance**
```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Run system tests
python -m pytest tests/ -v

# Performance analysis
python scripts/performance_analysis.py
```

#### **Monthly Maintenance**
```bash
# Security audit
python scripts/security_audit.py

# Data archival
python scripts/archive_data.py

# System optimization
python scripts/optimize_system.py
```

---

## 9. Troubleshooting

### 9.1 Common Issues

#### **Installation Issues**
```bash
# Python version issues
python --version  # Should be 3.9+

# Dependency conflicts
pip install --upgrade pip
pip install --force-reinstall -r requirements.txt

# Permission issues
sudo chown -R $USER:$USER /path/to/acd-monitor
chmod -R 755 /path/to/acd-monitor
```

#### **Configuration Issues**
```bash
# Environment variables
echo $ACD_MODE
echo $CHATBASE_API_KEY

# Configuration files
python scripts/validate_config.py

# Directory permissions
ls -la artifacts/
ls -la logs/
```

#### **Runtime Issues**
```bash
# Memory issues
free -h
ps aux | grep python

# Disk space
df -h
du -sh artifacts/

# Network issues
ping api.binance.com
curl -I https://api.binance.com
```

### 9.2 Error Handling

#### **Common Errors**
- **ImportError**: Missing dependencies
- **FileNotFoundError**: Missing configuration files
- **PermissionError**: Insufficient permissions
- **ConnectionError**: Network connectivity issues
- **TimeoutError**: API timeout issues

#### **Error Recovery**
```python
# Automatic retry
from src.acd.utils import retry_on_failure

@retry_on_failure(max_retries=3, delay=1)
def api_call():
    # API call implementation
    pass

# Graceful degradation
try:
    live_data = get_live_data()
except Exception as e:
    logger.warning(f"Live data unavailable: {e}")
    live_data = get_mock_data()
```

---

## 10. Security Considerations

### 10.1 API Security

#### **Authentication**
```python
# API key validation
def validate_api_key(api_key):
    # Validate API key format and permissions
    pass

# Rate limiting
from flask_limiter import Limiter

limiter = Limiter(
    app,
    key_func=lambda: request.remote_addr,
    default_limits=["100 per hour"]
)
```

#### **Data Encryption**
```python
# Encrypt sensitive data
from cryptography.fernet import Fernet

key = Fernet.generate_key()
cipher = Fernet(key)

encrypted_data = cipher.encrypt(sensitive_data)
decrypted_data = cipher.decrypt(encrypted_data)
```

### 10.2 Data Security

#### **Data Protection**
```python
# Data anonymization
def anonymize_data(data):
    # Remove or hash sensitive information
    pass

# Access control
def check_permissions(user, resource):
    # Check user permissions for resource access
    pass
```

#### **Audit Logging**
```python
# Audit trail
import logging

audit_logger = logging.getLogger('audit')
audit_logger.info(f"User {user} accessed {resource} at {timestamp}")
```

---

## 11. Performance Optimization

### 11.1 System Optimization

#### **Memory Optimization**
```python
# Memory-efficient data processing
import gc

def process_large_dataset(data):
    # Process data in chunks
    for chunk in data.chunks(1000):
        process_chunk(chunk)
        gc.collect()  # Force garbage collection
```

#### **CPU Optimization**
```python
# Parallel processing
from multiprocessing import Pool

def parallel_analysis(data_chunks):
    with Pool(processes=4) as pool:
        results = pool.map(analyze_chunk, data_chunks)
    return results
```

### 11.2 Database Optimization

#### **Query Optimization**
```python
# Efficient database queries
def get_market_data_optimized(exchange, pair, start_date, end_date):
    query = """
    SELECT * FROM market_data 
    WHERE exchange = %s AND pair = %s 
    AND timestamp BETWEEN %s AND %s
    ORDER BY timestamp
    """
    return execute_query(query, (exchange, pair, start_date, end_date))
```

#### **Indexing**
```sql
-- Create indexes for better performance
CREATE INDEX idx_market_data_exchange_pair ON market_data(exchange, pair);
CREATE INDEX idx_market_data_timestamp ON market_data(timestamp);
```

---

## 12. Backup and Recovery

### 12.1 Backup Procedures

#### **Data Backup**
```bash
# Backup artifacts
tar -czf artifacts_backup_$(date +%Y%m%d).tar.gz artifacts/

# Backup configuration
cp -r config/ config_backup_$(date +%Y%m%d)/

# Backup logs
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/
```

#### **Database Backup**
```bash
# PostgreSQL backup
pg_dump -h localhost -U acd_user acd_db > acd_backup_$(date +%Y%m%d).sql

# MongoDB backup
mongodump --host localhost --port 27017 --db acd_db --out backup_$(date +%Y%m%d)
```

### 12.2 Recovery Procedures

#### **Data Recovery**
```bash
# Restore artifacts
tar -xzf artifacts_backup_20250921.tar.gz

# Restore configuration
cp -r config_backup_20250921/* config/

# Restore logs
tar -xzf logs_backup_20250921.tar.gz
```

#### **System Recovery**
```bash
# Reinstall system
pip install -r requirements.txt

# Restore configuration
cp config_backup_20250921/config.yaml config/

# Restart services
systemctl restart acd-service
```

---

## 13. Conclusion

This deployment guide provides comprehensive instructions for deploying the ACD system in various environments. The guide covers installation, configuration, operation, monitoring, and maintenance procedures.

For additional support or questions, please refer to the troubleshooting section or contact the development team.

---

**Document Status**: COMPLETED - Version 1.0  
**Prepared by**: Theo (AI Assistant)  
**Date**: September 21, 2025  
**Next Review**: End of Week 4


