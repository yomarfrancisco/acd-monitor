# Algorithmic Coordination Diagnostic (ACD) Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![CI](https://github.com/yomarfrancisco/acd-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/yomarfrancisco/acd-monitor/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/yomarfrancisco/acd-monitor/branch/main/graph/badge.svg)](https://codecov.io/gh/yomarfrancisco/acd-monitor)

## Executive Summary

The Algorithmic Coordination Diagnostic (ACD) is a continuous monitoring platform that distinguishes legitimate algorithmic competition from anticompetitive coordination using empirically grounded econometric methods. Built on the methodological foundation of RBB Brief 55+, the ACD applies Invariant Causal Prediction (ICP) and Variational Method of Moments (VMM) to detect structural stability in pricing relationships across changing market environments.

**Core Value Proposition:** Continuous compliance monitoring for algorithm-intensive firms, providing defensible evidence of competitive behavior while enabling early detection of coordination risks.

## Key Features

- **Dual Pillar Analytics:** ICP + VMM methodology for robust coordination detection
- **Multi-Tier Data Strategy:** Client feeds + independent global sources + local proxies + derived signals
- **Real-Time Monitoring:** Continuous VMM updates every 5 minutes with regime change detection
- **Regulatory Credibility:** Cryptographic timestamping, immutable audit trails, court-admissible evidence
- **Enterprise Focus:** Subscription model targeting financial institutions, tech firms, and airlines

## Anchor Documents

The ACD platform is built on three foundational documents:

- **[Brief 55+](docs/briefs/brief55+.md)** - Methodological foundation (dual pillars: ICP + VMM)
- **[Mission Control](docs/mission_control.md)** - Operational execution framework  
- **[Product Spec v1.8](docs/product_spec_v1.8.md)** - Complete technical specification

**Note:** Brief 55+ and Mission Control are immutable reference anchors. The Product Spec evolves with development (v1.9, v2.0, etc.).

## Product Specification Summary (v1.8)

### Core Analytics Engine

**Pillar 1: Invariant Causal Prediction (ICP)**
- Tests structural stability of pricing relationships across market environments
- Provides formal statistical tests for coordination vs. competition
- Handles multiple environmental dimensions simultaneously

**Pillar 2: Variational Method of Moments (VMM)**
- Continuous monitoring engine adapted from financial risk management
- Real-time structural deterioration detection
- Dynamic confidence scoring with evolving intervals

### Risk Scoring (0-100)

- **LOW (0-33):** Competitive behavior indicated
- **AMBER (34-66):** Monitoring recommended  
- **RED (67-100):** Investigation warranted

### Target Markets (Revenue Priority)

1. **Financial Institutions & Defendants** - Enterprise subscriptions ($500K-$2M/year)
2. **Legal & Compliance Teams** - Case-based consulting + retainers
3. **Competition Authorities** - Pilot programs + licensing fees

### Technical Architecture

- **Backend:** Python/FastAPI, PostgreSQL, Redis, Celery
- **Frontend:** React/TypeScript, Material-UI, D3.js/Chart.js
- **Infrastructure:** Kubernetes, AWS/GCP, Docker
- **Security:** OAuth2/JWT, AES-256, RFC 3161 timestamping

### Implementation Roadmap

- **Phase 1 (Months 1-6):** Pilot validation with FNB CDS market
- **Phase 2 (Months 7-12):** Regulatory sandbox deployment
- **Phase 3 (Year 2):** Industry compliance programs
- **Phase 4 (Year 3):** Full commercial rollout

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 6+
- Docker & Docker Compose

### Installation

```bash
# Clone the repository
git clone https://github.com/rbb-economics/acd-monitor.git
cd acd-monitor

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
python scripts/setup_db.py

# Start the application
python src/backend/main.py
```

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run linting
flake8 src/ tests/

# Generate golden datasets
python scripts/generate_golden.py
```

## Project Structure

```
acd-monitor/
├── docs/                          # Documentation
│   ├── briefs/                   # Methodological foundations
│   │   └── brief55+.md          # RBB Brief 55+ (immutable)
│   ├── mission_control.md        # Operational framework (immutable)
│   └── product_spec_v1.8.md     # Technical specification (evolving)
├── src/                          # Source code
│   ├── backend/                  # FastAPI backend
│   ├── frontend/                 # React frontend
│   └── analytics/                # Core econometric engine
├── schemas/                      # JSON schemas
├── tests/                        # Test suite
├── data/                         # Data and golden datasets
├── scripts/                      # Utility scripts
└── acceptance/                   # Acceptance criteria
```

## Testing & Validation

- **Golden Datasets:** Synthetic competitive, synthetic coordinated, real public CDS sample
- **Contract Tests:** OpenAPI validation, JSON schema compliance
- **Deterministic Pipelines:** Seeded randomness, pinned library versions
- **Performance Benchmarks:** Latency, accuracy, scalability tests

## CI / Coverage

- **Automated Testing:** Lint, format check, pytest with coverage
- **Coverage Upload:** Set `CODECOV_TOKEN` repo secret for coverage upload (private repos). Public repos may omit.
- **Future:** Public repos can switch to tokenless OIDC for enhanced security.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation:** [docs/](docs/)
- **Issues:** [GitHub Issues](https://github.com/rbb-economics/acd-monitor/issues)
- **Discussions:** [GitHub Discussions](https://github.com/rbb-economics/acd-monitor/discussions)

---

**Built by [Ygor Francisco](mailto:ygor.francisco@gmail.com)**

*The ACD platform operationalizes the methodological framework developed in RBB Brief 55+ to provide empirically grounded tools for algorithmic coordination detection.*
