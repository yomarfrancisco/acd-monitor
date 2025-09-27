# ACD Monitor

[![CI/CD Pipeline](https://github.com/yomarfrancisco/acd-monitor/actions/workflows/ci.yaml/badge.svg)](https://github.com/yomarfrancisco/acd-monitor/actions/workflows/ci.yaml)
[![Release](https://github.com/yomarfrancisco/acd-monitor/actions/workflows/release.yaml/badge.svg)](https://github.com/yomarfrancisco/acd-monitor/actions/workflows/release.yaml)
[![Latest Release](https://img.shields.io/github/v/release/yomarfrancisco/acd-monitor)](https://github.com/yomarfrancisco/acd-monitor/releases/latest)

## Overview

ACD Monitor is a comprehensive cryptocurrency market surveillance system that detects bilateral collusion patterns, analyzes microstructure dynamics, and provides regulatory compliance reporting.

## Features

- **Real-time Data Capture**: Live tick data from 5 major exchanges (Binance, Coinbase, Kraken, OKX, Bybit)
- **Bilateral Collusion Detection**: Identifies potential coordination between venue pairs
- **Microstructure Analysis**: InfoShare, Spread Convergence, Lead-Lag analysis
- **Regulatory Reporting**: Automated evidence generation and compliance reporting
- **Pairwise Analysis**: Comprehensive analysis of all 10 possible venue combinations

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run live capture
python src/acd/capture/overlap_orchestrator.py --pair BTC-USD --export-dir exports --verbose

# Run pairwise analysis
python scripts/run_pairwise_analysis.py --export-dir exports/sweep_recon_best2_live --verbose
```

## Key Components

### Capture System
- **Overlap Orchestrator**: Concurrent data capture with strict overlap detection
- **Real-time Monitoring**: Heartbeat tracking and status reporting
- **Data Persistence**: Parquet-based storage with time-based partitioning

### Analysis Pipeline
- **InfoShare Analysis**: Information leadership detection
- **Spread Convergence**: Coordinated trading pattern identification
- **Lead-Lag Analysis**: Cross-venue timing relationships

### Regulatory Reporting
- **Evidence Bundles**: Comprehensive analysis results
- **Decision Logging**: Automated regulatory flagging
- **Provenance Tracking**: Complete audit trail

## Recent Findings

### Bilateral Collusion Detection
- **binance+bybit**: Clear bilateral collusion detected (InfoShare=0.602, Coordination=0.860)
- **Threshold Breaches**: Multiple pairs exceed regulatory thresholds
- **Market Impact**: Significant coordination patterns identified

### Pairwise Analysis Results
- **Total Pairs Analyzed**: 10 possible venue combinations
- **Successful Analyses**: 12 bundles (6 pairs × 2 granularities)
- **Regulatory Compliance**: Comprehensive threshold analysis

## CI/CD Status

- **Build Status**: [![CI/CD Pipeline](https://github.com/yomarfrancisco/acd-monitor/actions/workflows/ci.yaml/badge.svg)](https://github.com/yomarfrancisco/acd-monitor/actions/workflows/ci.yaml)
- **Latest Release**: [![Latest Release](https://img.shields.io/github/v/release/yomarfrancisco/acd-monitor)](https://github.com/yomarfrancisco/acd-monitor/releases/latest)
- **Artifacts**: Automated artifact collection and release management

## Documentation

- **Working Plan**: [ACD_Working_Plan.md](ACD_Working_Plan.md)
- **API Documentation**: [docs/](docs/)
- **Examples**: [examples/](examples/)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

For questions or support, please open an issue or contact the maintainers.
