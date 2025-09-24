# ACD API Documentation

**Project**: Algorithmic Coordination Diagnostic (ACD) - Phase 4: Regulatory Pilot Deployment  
**Date**: September 21, 2025  
**Version**: 1.0  
**Prepared by**: Theo (AI Assistant)  

---

## 1. Overview

The ACD API provides programmatic access to the Algorithmic Coordination Diagnostic system. The API supports both REST and WebSocket interfaces for real-time analysis, bundle generation, and data management.

### 1.1 Base URL
```
Production: https://api.acd-monitor.com
Staging: https://staging-api.acd-monitor.com
Development: http://localhost:8000
```

### 1.2 Authentication
All API requests require authentication using API keys:
```bash
Authorization: Bearer YOUR_API_KEY
```

### 1.3 Rate Limits
- **Standard**: 100 requests per hour
- **Premium**: 1000 requests per hour
- **Enterprise**: 10000 requests per hour

---

## 2. REST API Endpoints

### 2.1 Health and Status

#### **Health Check**
```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-21T19:45:00Z",
  "version": "1.0.0",
  "uptime": 86400
}
```

#### **Detailed Health Check**
```http
GET /api/health/detailed
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-21T19:45:00Z",
  "version": "1.0.0",
  "uptime": 86400,
  "components": {
    "database": "healthy",
    "cache": "healthy",
    "external_apis": "healthy"
  },
  "metrics": {
    "cpu_usage": 45.2,
    "memory_usage": 67.8,
    "disk_usage": 23.1
  }
}
```

### 2.2 Analysis Endpoints

#### **ICP Analysis**
```http
POST /api/analysis/icp
```

**Request Body:**
```json
{
  "data": {
    "exchanges": ["binance", "coinbase", "kraken"],
    "pairs": ["BTC/USD", "ETH/USD"],
    "time_period": "last_30_days"
  },
  "config": {
    "significance_level": 0.05,
    "bootstrap_samples": 1000,
    "min_samples_per_env": 100
  }
}
```

**Response:**
```json
{
  "analysis_id": "icp_analysis_12345",
  "status": "completed",
  "results": {
    "test_statistic": 15.7,
    "p_value": 0.013,
    "n_environments": 3,
    "confidence_interval": [0.15, 0.25],
    "bootstrap_ci": [0.12, 0.28]
  },
  "metadata": {
    "execution_time": 2.3,
    "data_points": 10000,
    "timestamp": "2025-09-21T19:45:00Z"
  }
}
```

#### **VMM Analysis**
```http
POST /api/analysis/vmm
```

**Request Body:**
```json
{
  "data": {
    "exchanges": ["binance", "coinbase", "kraken"],
    "pairs": ["BTC/USD", "ETH/USD"],
    "time_period": "last_30_days"
  },
  "config": {
    "convergence_tolerance": 1e-6,
    "max_iterations": 1000,
    "regularization": 0.01
  }
}
```

**Response:**
```json
{
  "analysis_id": "vmm_analysis_12345",
  "status": "completed",
  "results": {
    "final_loss": 0.023,
    "beta_estimates": [0.15, 0.22, 0.18],
    "sigma_estimates": [0.12, 0.15, 0.13],
    "rho_estimates": [0.45, 0.52, 0.48],
    "over_identification_stat": 8.3,
    "over_identification_p_value": 0.041
  },
  "metadata": {
    "execution_time": 1.8,
    "iterations": 156,
    "timestamp": "2025-09-21T19:45:00Z"
  }
}
```

#### **Validation Analysis**
```http
POST /api/analysis/validation
```

**Request Body:**
```json
{
  "data": {
    "exchanges": ["binance", "coinbase", "kraken"],
    "pairs": ["BTC/USD", "ETH/USD"],
    "time_period": "last_30_days"
  },
  "config": {
    "lead_lag": {
      "window_size": 30,
      "min_observations": 50
    },
    "mirroring": {
      "similarity_threshold": 0.7,
      "min_observations": 50
    },
    "hmm": {
      "n_states": 3,
      "max_iterations": 100
    },
    "infoflow": {
      "transfer_entropy_threshold": 0.1
    }
  }
}
```

**Response:**
```json
{
  "analysis_id": "validation_analysis_12345",
  "status": "completed",
  "results": {
    "lead_lag": {
      "switching_entropy": 0.15,
      "avg_granger_p": 0.023,
      "n_windows": 25
    },
    "mirroring": {
      "mirroring_ratio": 0.78,
      "coordination_score": 0.65,
      "avg_cosine_similarity": 0.82
    },
    "hmm": {
      "n_states": 3,
      "transition_matrix": [[0.7, 0.2, 0.1], [0.3, 0.5, 0.2], [0.1, 0.3, 0.6]],
      "dwell_times": {"state_0": 45, "state_1": 38, "state_2": 52}
    },
    "infoflow": {
      "transfer_entropy": 0.15,
      "network_density": 0.65,
      "out_degree_concentration": 0.78
    }
  },
  "metadata": {
    "execution_time": 3.2,
    "timestamp": "2025-09-21T19:45:00Z"
  }
}
```

#### **Integrated Analysis**
```http
POST /api/analysis/integrated
```

**Request Body:**
```json
{
  "data": {
    "exchanges": ["binance", "coinbase", "kraken"],
    "pairs": ["BTC/USD", "ETH/USD"],
    "time_period": "last_30_days"
  },
  "config": {
    "icp": {
      "significance_level": 0.05,
      "bootstrap_samples": 1000
    },
    "vmm": {
      "convergence_tolerance": 1e-6,
      "max_iterations": 1000
    },
    "validation": {
      "lead_lag": {"window_size": 30},
      "mirroring": {"similarity_threshold": 0.7},
      "hmm": {"n_states": 3},
      "infoflow": {"transfer_entropy_threshold": 0.1}
    }
  }
}
```

**Response:**
```json
{
  "analysis_id": "integrated_analysis_12345",
  "status": "completed",
  "results": {
    "composite_score": 75.5,
    "risk_level": "AMBER",
    "confidence_level": 0.85,
    "coordination_detected": true,
    "icp_results": {
      "test_statistic": 15.7,
      "p_value": 0.013,
      "n_environments": 3
    },
    "vmm_results": {
      "final_loss": 0.023,
      "over_identification_p_value": 0.041
    },
    "validation_results": {
      "lead_lag": {"switching_entropy": 0.15},
      "mirroring": {"mirroring_ratio": 0.78},
      "hmm": {"n_states": 3},
      "infoflow": {"transfer_entropy": 0.15}
    }
  },
  "metadata": {
    "execution_time": 5.7,
    "timestamp": "2025-09-21T19:45:00Z"
  }
}
```

### 2.3 Bundle Generation Endpoints

#### **Generate Bundle**
```http
POST /api/bundles/generate
```

**Request Body:**
```json
{
  "analysis_id": "integrated_analysis_12345",
  "bundle_type": "regulatory",
  "config": {
    "include_attribution": true,
    "include_provenance": true,
    "include_alternative_explanations": true,
    "output_formats": ["json", "pdf"]
  }
}
```

**Response:**
```json
{
  "bundle_id": "bundle_67890",
  "status": "completed",
  "files": {
    "json": "/api/bundles/bundle_67890/download?format=json",
    "pdf": "/api/bundles/bundle_67890/download?format=pdf",
    "attribution": "/api/bundles/bundle_67890/download?format=attribution",
    "provenance": "/api/bundles/bundle_67890/download?format=provenance"
  },
  "metadata": {
    "generation_time": 1.2,
    "file_sizes": {
      "json": 245760,
      "pdf": 1024000,
      "attribution": 51200,
      "provenance": 25600
    },
    "timestamp": "2025-09-21T19:45:00Z"
  }
}
```

#### **Get Bundle Status**
```http
GET /api/bundles/{bundle_id}
```

**Response:**
```json
{
  "bundle_id": "bundle_67890",
  "status": "completed",
  "created_at": "2025-09-21T19:45:00Z",
  "completed_at": "2025-09-21T19:45:01Z",
  "files": {
    "json": "/api/bundles/bundle_67890/download?format=json",
    "pdf": "/api/bundles/bundle_67890/download?format=pdf"
  },
  "metadata": {
    "analysis_id": "integrated_analysis_12345",
    "bundle_type": "regulatory",
    "file_count": 4
  }
}
```

#### **Download Bundle**
```http
GET /api/bundles/{bundle_id}/download?format={format}
```

**Parameters:**
- `format`: `json`, `pdf`, `attribution`, `provenance`

**Response:**
- **JSON**: JSON file download
- **PDF**: PDF file download
- **Attribution**: Attribution table JSON
- **Provenance**: Provenance metadata JSON

### 2.4 Data Management Endpoints

#### **Get Market Data**
```http
GET /api/data/market
```

**Query Parameters:**
- `exchanges`: Comma-separated list of exchanges
- `pairs`: Comma-separated list of trading pairs
- `start_date`: Start date (ISO 8601 format)
- `end_date`: End date (ISO 8601 format)
- `limit`: Maximum number of records (default: 1000)

**Example:**
```http
GET /api/data/market?exchanges=binance,coinbase&pairs=BTC/USD,ETH/USD&start_date=2025-09-01&end_date=2025-09-21&limit=5000
```

**Response:**
```json
{
  "data": [
    {
      "timestamp": "2025-09-21T19:45:00Z",
      "exchange": "binance",
      "pair": "BTC/USD",
      "bid_price": 45000.0,
      "ask_price": 45010.0,
      "bid_volume": 1.5,
      "ask_volume": 2.1,
      "spread": 10.0
    }
  ],
  "metadata": {
    "total_records": 5000,
    "exchanges": ["binance", "coinbase"],
    "pairs": ["BTC/USD", "ETH/USD"],
    "time_range": {
      "start": "2025-09-01T00:00:00Z",
      "end": "2025-09-21T23:59:59Z"
    }
  }
}
```

#### **Upload Data**
```http
POST /api/data/upload
```

**Request Body:**
```json
{
  "data": [
    {
      "timestamp": "2025-09-21T19:45:00Z",
      "exchange": "binance",
      "pair": "BTC/USD",
      "bid_price": 45000.0,
      "ask_price": 45010.0,
      "bid_volume": 1.5,
      "ask_volume": 2.1
    }
  ],
  "metadata": {
    "source": "manual_upload",
    "validation": true
  }
}
```

**Response:**
```json
{
  "upload_id": "upload_12345",
  "status": "completed",
  "records_processed": 1000,
  "records_valid": 995,
  "records_invalid": 5,
  "errors": [
    {
      "record": 15,
      "error": "Invalid timestamp format"
    }
  ],
  "metadata": {
    "processing_time": 0.5,
    "timestamp": "2025-09-21T19:45:00Z"
  }
}
```

#### **Get Data Status**
```http
GET /api/data/status
```

**Response:**
```json
{
  "status": "healthy",
  "data_sources": {
    "binance": {
      "status": "active",
      "last_update": "2025-09-21T19:45:00Z",
      "records_count": 1000000
    },
    "coinbase": {
      "status": "active",
      "last_update": "2025-09-21T19:44:30Z",
      "records_count": 800000
    },
    "kraken": {
      "status": "active",
      "last_update": "2025-09-21T19:44:45Z",
      "records_count": 600000
    }
  },
  "total_records": 2400000,
  "last_updated": "2025-09-21T19:45:00Z"
}
```

---

## 3. WebSocket API

### 3.1 Real-time Analysis

#### **Connection**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/analysis');

ws.onopen = function(event) {
    console.log('Connected to ACD WebSocket');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

ws.onclose = function(event) {
    console.log('Disconnected from ACD WebSocket');
};
```

#### **Subscribe to Analysis**
```javascript
// Subscribe to real-time analysis
ws.send(JSON.stringify({
    type: 'subscribe',
    channel: 'analysis',
    config: {
        exchanges: ['binance', 'coinbase'],
        pairs: ['BTC/USD', 'ETH/USD'],
        analysis_type: 'integrated'
    }
}));
```

#### **Analysis Updates**
```json
{
  "type": "analysis_update",
  "analysis_id": "realtime_analysis_12345",
  "timestamp": "2025-09-21T19:45:00Z",
  "results": {
    "composite_score": 75.5,
    "risk_level": "AMBER",
    "coordination_detected": true
  },
  "metadata": {
    "data_points": 1000,
    "processing_time": 0.1
  }
}
```

### 3.2 Real-time Data

#### **Subscribe to Market Data**
```javascript
// Subscribe to market data
ws.send(JSON.stringify({
    type: 'subscribe',
    channel: 'market_data',
    config: {
        exchanges: ['binance', 'coinbase'],
        pairs: ['BTC/USD', 'ETH/USD']
    }
}));
```

#### **Market Data Updates**
```json
{
  "type": "market_data_update",
  "timestamp": "2025-09-21T19:45:00Z",
  "data": {
    "exchange": "binance",
    "pair": "BTC/USD",
    "bid_price": 45000.0,
    "ask_price": 45010.0,
    "spread": 10.0
  }
}
```

---

## 4. Error Handling

### 4.1 HTTP Status Codes

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request parameters
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error
- **502 Bad Gateway**: External service error
- **503 Service Unavailable**: Service temporarily unavailable

### 4.2 Error Response Format

```json
{
  "error": {
    "code": "INVALID_PARAMETERS",
    "message": "Invalid request parameters",
    "details": {
      "field": "exchanges",
      "issue": "At least one exchange must be specified"
    },
    "timestamp": "2025-09-21T19:45:00Z",
    "request_id": "req_12345"
  }
}
```

### 4.3 Common Error Codes

- **INVALID_PARAMETERS**: Invalid request parameters
- **AUTHENTICATION_FAILED**: Authentication failed
- **RATE_LIMIT_EXCEEDED**: Rate limit exceeded
- **DATA_NOT_FOUND**: Requested data not found
- **ANALYSIS_FAILED**: Analysis execution failed
- **BUNDLE_GENERATION_FAILED**: Bundle generation failed
- **EXTERNAL_SERVICE_ERROR**: External service error
- **INTERNAL_SERVER_ERROR**: Internal server error

---

## 5. SDKs and Libraries

### 5.1 Python SDK

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
    analysis_id=results['analysis_id'],
    bundle_type='regulatory'
)

# Download bundle
bundle.download('./output/')
```

### 5.2 JavaScript SDK

#### **Installation**
```bash
npm install acd-sdk
```

#### **Usage**
```javascript
import { ACDClient } from 'acd-sdk';

// Initialize client
const client = new ACDClient({
    apiKey: 'your_api_key',
    baseUrl: 'http://localhost:8000'
});

// Run analysis
const results = await client.runAnalysis({
    exchanges: ['binance', 'coinbase'],
    pairs: ['BTC/USD', 'ETH/USD'],
    timePeriod: 'last_30_days'
});

// Generate bundle
const bundle = await client.generateBundle({
    analysisId: results.analysisId,
    bundleType: 'regulatory'
});

// Download bundle
await bundle.download('./output/');
```

### 5.3 R SDK

#### **Installation**
```r
install.packages("acdR")
```

#### **Usage**
```r
library(acdR)

# Initialize client
client <- ACDClient$new(
    api_key = "your_api_key",
    base_url = "http://localhost:8000"
)

# Run analysis
results <- client$run_analysis(
    exchanges = c("binance", "coinbase"),
    pairs = c("BTC/USD", "ETH/USD"),
    time_period = "last_30_days"
)

# Generate bundle
bundle <- client$generate_bundle(
    analysis_id = results$analysis_id,
    bundle_type = "regulatory"
)

# Download bundle
bundle$download("./output/")
```

---

## 6. Examples

### 6.1 Complete Analysis Workflow

#### **Python Example**
```python
from acd_sdk import ACDClient
import time

# Initialize client
client = ACDClient(
    api_key='your_api_key',
    base_url='http://localhost:8000'
)

# Step 1: Run integrated analysis
print("Running integrated analysis...")
analysis = client.run_analysis(
    exchanges=['binance', 'coinbase', 'kraken'],
    pairs=['BTC/USD', 'ETH/USD'],
    time_period='last_30_days',
    analysis_type='integrated'
)

# Step 2: Wait for completion
while analysis['status'] != 'completed':
    time.sleep(1)
    analysis = client.get_analysis_status(analysis['analysis_id'])

print(f"Analysis completed: {analysis['results']['composite_score']}")

# Step 3: Generate bundle
print("Generating regulatory bundle...")
bundle = client.generate_bundle(
    analysis_id=analysis['analysis_id'],
    bundle_type='regulatory',
    include_attribution=True,
    include_provenance=True
)

# Step 4: Download bundle
print("Downloading bundle...")
bundle.download('./output/regulatory_bundle/')

print("Workflow completed successfully!")
```

#### **JavaScript Example**
```javascript
import { ACDClient } from 'acd-sdk';

async function runAnalysisWorkflow() {
    // Initialize client
    const client = new ACDClient({
        apiKey: 'your_api_key',
        baseUrl: 'http://localhost:8000'
    });

    try {
        // Step 1: Run integrated analysis
        console.log('Running integrated analysis...');
        const analysis = await client.runAnalysis({
            exchanges: ['binance', 'coinbase', 'kraken'],
            pairs: ['BTC/USD', 'ETH/USD'],
            timePeriod: 'last_30_days',
            analysisType: 'integrated'
        });

        // Step 2: Wait for completion
        while (analysis.status !== 'completed') {
            await new Promise(resolve => setTimeout(resolve, 1000));
            const updatedAnalysis = await client.getAnalysisStatus(analysis.analysisId);
            Object.assign(analysis, updatedAnalysis);
        }

        console.log(`Analysis completed: ${analysis.results.compositeScore}`);

        // Step 3: Generate bundle
        console.log('Generating regulatory bundle...');
        const bundle = await client.generateBundle({
            analysisId: analysis.analysisId,
            bundleType: 'regulatory',
            includeAttribution: true,
            includeProvenance: true
        });

        // Step 4: Download bundle
        console.log('Downloading bundle...');
        await bundle.download('./output/regulatory_bundle/');

        console.log('Workflow completed successfully!');
    } catch (error) {
        console.error('Workflow failed:', error);
    }
}

runAnalysisWorkflow();
```

### 6.2 Real-time Monitoring

#### **WebSocket Example**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/analysis');

ws.onopen = function(event) {
    console.log('Connected to ACD WebSocket');
    
    // Subscribe to real-time analysis
    ws.send(JSON.stringify({
        type: 'subscribe',
        channel: 'analysis',
        config: {
            exchanges: ['binance', 'coinbase'],
            pairs: ['BTC/USD', 'ETH/USD'],
            analysisType: 'integrated'
        }
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    switch (data.type) {
        case 'analysis_update':
            console.log(`Risk Level: ${data.results.riskLevel}`);
            console.log(`Composite Score: ${data.results.compositeScore}`);
            break;
            
        case 'error':
            console.error('WebSocket error:', data.error);
            break;
            
        default:
            console.log('Received:', data);
    }
};

ws.onclose = function(event) {
    console.log('Disconnected from ACD WebSocket');
};

ws.onerror = function(error) {
    console.error('WebSocket error:', error);
};
```

---

## 7. Best Practices

### 7.1 API Usage

#### **Rate Limiting**
- Implement exponential backoff for rate limit errors
- Use appropriate request intervals
- Monitor rate limit headers

#### **Error Handling**
- Always check response status codes
- Implement retry logic for transient errors
- Log errors for debugging

#### **Authentication**
- Store API keys securely
- Rotate API keys regularly
- Use environment variables for configuration

### 7.2 Performance Optimization

#### **Request Optimization**
- Use appropriate time periods
- Limit data requests to necessary exchanges/pairs
- Use pagination for large datasets

#### **Caching**
- Cache analysis results when appropriate
- Use conditional requests for data updates
- Implement client-side caching

#### **Concurrent Requests**
- Use appropriate concurrency limits
- Implement request queuing
- Monitor system resources

---

## 8. Conclusion

This API documentation provides comprehensive information for integrating with the ACD system. The API supports both REST and WebSocket interfaces, with SDKs available for multiple programming languages.

For additional support or questions, please refer to the troubleshooting section or contact the development team.

---

**Document Status**: COMPLETED - Version 1.0  
**Prepared by**: Theo (AI Assistant)  
**Date**: September 21, 2025  
**Next Review**: End of Week 4



