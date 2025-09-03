# Algorithmic Coordination Diagnostic — Full Specification

## Core Analytics
- **Environment detection**: Change-point detection (PELT) to split CDS time series
- **Invariant Causal Prediction (ICP)**: OLS regressions across environments, Chow/Wald tests for invariance
- **Price synchronization**: Lagged correlations controlling for macro shocks
- **Regime detection**: Variational Bayesian HMM
- **Information flow**: Granger causality, network centrality
- **Composite score**: 0.35×INV + 0.25×FLOW + 0.25×REG + 0.15×SYNC

## Technical Architecture
- **Backend**: Python/FastAPI + PostgreSQL
- **Processing**: Pandas/Numpy + Kafka stream
- **Frontend**: React + Material UI + Chart.js
- **Infrastructure**: Kubernetes, Redis, S3, OpenTelemetry

## Data Quality & Fallback
- Client CDS quotes → Independent feeds (S&P, ICE, Refinitiv, JSE) → Derived bond-CDS basis
- ±5bps discrepancy threshold for validation
- Confidence scoring 0–100
- Fallback triggers: auto (silent feed >X mins), manual (legal override)
- Mixed frequency handled via interpolation (<10m gaps) + 1-min rollups

## Legal & Compliance
- SA Competition Act, EU Art. 101, UK Ch. I, US Section 1
- Cryptographic timestamping (RFC 3161)
- Audit logs with source change records
- Evidence packs: raw data + source logs + confidence scores

## Success Metrics
- 99.9% uptime regardless of client data
- 95%+ alignment with economist manual assessments
- <5 min analysis on 10–20m observations
