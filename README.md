# Algorithmic Coordination Diagnostic (ACD)

The Algorithmic Coordination Diagnostic (ACD) is an **agent-driven monitoring system** that identifies and explains algorithmic coordination risks in real-time. Combining causal inference, environment partitioning, and continuous validation with natural-language reporting, ACD detects collusion signals and generates court-ready outputs that regulators, firms, and judges can easily understand and act on.

Built on the methodological foundation of RBB Brief 55+, the ACD applies Invariant Causal Prediction (ICP) and Variational Method of Moments (VMM) to detect structural stability in pricing relationships across changing market environments.

**Core Value**: An intelligent agent that continuously monitors your pricing algorithms, detects coordination risks, and generates court-ready evidence - combining Brief 55+ methodology with natural-language reporting that compliance teams, regulators, and legal professionals can immediately understand and act on.

## Key Features

- **Dual Pillar Analytics**: ICP + VMM methodology for robust coordination detection
- **Multi-Tier Data Strategy**: Client feeds + independent global sources + local proxies + derived signals  
- **Real-Time Intelligence**: Continuous VMM updates every 5 minutes with natural-language risk summaries
- **Regulatory Credibility**: Cryptographic timestamping, immutable audit trails, court-admissible evidence
- **Enterprise Focus**: Subscription model targeting financial institutions, tech firms, and airlines

## Agent Architecture

- **Continuous Intelligence**: 5-minute monitoring cycles with contextual business risk summaries
- **Natural-Language Reporting**: Automatically translates complex econometric findings into clear explanations
- **Proactive Alerting**: Early warning system with business-friendly risk classifications
- **Evidence Generation**: Timestamped, cryptographically verified audit trails ready for regulatory submission
- **Contextual Analysis**: Explains *why* patterns indicate competition vs coordination using environment sensitivity

## Methodological Foundation

The ACD platform is built on three foundational documents:

- **[Brief 55+](docs/briefs/brief55+.md)** - Methodological foundation (dual pillars: ICP + VMM)
- **[Mission Control](docs/mission_control.md)** - Operational execution framework  
- **[Product Spec v2.2](docs/product_spec_v2.2.md)** - Complete technical specification

*Note: Brief 55+ and Mission Control are immutable reference anchors. The Product Spec evolves with development (v1.9, v2.0, v2.2, etc.).*

## Methodology

### Pillar 1: Invariant Causal Prediction (ICP)
- Tests structural stability of pricing relationships across market environments
- Provides formal statistical tests for coordination vs. competition
- Handles multiple environmental dimensions simultaneously

### Pillar 2: Variational Method of Moments (VMM)  
- Continuous monitoring engine adapted from financial risk management
- Real-time structural deterioration detection
- Dynamic confidence scoring with evolving intervals

## Risk Classification

The ACD agent provides continuous risk scoring with clear business interpretation:

- **LOW (0-33)**: Competitive behavior indicated - algorithms showing healthy environment sensitivity
- **AMBER (34-66)**: Monitoring recommended - patterns warrant closer examination
- **RED (67-100)**: Investigation warranted - invariant relationships suggest coordination risk

## Commercial Applications

### Target Markets
- **Financial Institutions & Defendants**: Enterprise agent subscriptions ($500K-$2M/year)
- **Legal & Compliance Teams**: Case-based consulting + retainers with agent-generated evidence packages
- **Competition Authorities**: Pilot programs + licensing fees for investigative tooling

### Value Propositions
- **Proactive Compliance**: Continuous agent monitoring prevents regulatory surprises
- **Litigation Defense**: Agent-generated expert testimony and court-ready evidence
- **Regulatory Preparation**: Pre-investigation compliance validation with defensible documentation
- **Risk Management**: Early detection of problematic algorithmic patterns before enforcement action

## Technology Stack

- **Backend**: Python/FastAPI, PostgreSQL, Redis, Celery
- **Frontend**: React/TypeScript, Material-UI, D3.js/Chart.js  
- **Infrastructure**: Kubernetes, AWS/GCP, Docker
- **Security**: OAuth2/JWT, AES-256, RFC 3161 timestamping

## Implementation Roadmap

- **Phase 1 (Months 1-6)**: Pilot validation with FNB CDS market
- **Phase 2 (Months 7-12)**: Regulatory sandbox deployment  
- **Phase 3 (Year 2)**: Industry compliance programs
- **Phase 4 (Year 3)**: Full commercial rollout

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 6+
- Docker & Docker Compose

## Quick Start

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

## Development

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
├── docs/                    # Documentation
│   ├── briefs/             # Methodological foundations
│   │   └── brief55+.md     # RBB Brief 55+ (immutable)
│   ├── mission_control.md  # Operational framework (immutable)
│   └── product_spec_v2.2.md # Technical specification (evolving)
├── src/                    # Source code
│   ├── backend/           # FastAPI backend
│   ├── frontend/          # React frontend
│   └── analytics/         # Core econometric engine
├── schemas/               # JSON schemas
├── tests/                # Test suite
├── data/                 # Data and golden datasets
├── scripts/              # Utility scripts
└── acceptance/           # Acceptance criteria
```

## Quality Assurance

- **Golden Datasets**: Synthetic competitive, synthetic coordinated, real public CDS sample
- **Contract Tests**: OpenAPI validation, JSON schema compliance  
- **Deterministic Pipelines**: Seeded randomness, pinned library versions
- **Performance Benchmarks**: Latency, accuracy, scalability tests
- **Automated Testing**: Lint, format check, pytest with coverage

## CI/CD Pipeline

- **Coverage Upload**: Set `CODECOV_TOKEN` repo secret for coverage upload (private repos). Public repos may omit.
- **Future**: Public repos can switch to tokenless OIDC for enhanced security.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)  
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Specs & Docs

- **Product Specification v2.2 (current):** [Markdown](docs/product_spec_v2.2.md) • [PDF](docs/ACD_Product_Spec_v2.2.pdf)
- **Brief 55+ (immutable):** docs/briefs/Brief-55+.pdf
- **Mission Control (immutable):** docs/mission_control.md

## Support & Documentation

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/rbb-economics/acd-monitor/issues)
- **Discussions**: [GitHub Discussions](https://github.com/rbb-economics/acd-monitor/discussions)

---

**Built by [Ygor Francisco](mailto:ygor.francisco@gmail.com)**

*The ACD platform operationalizes the methodological framework developed in RBB Brief 55+ to provide empirically grounded, agent-driven tools for algorithmic coordination detection.*