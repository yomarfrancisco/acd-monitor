# ACD Monitor - Backend Operations
# End-to-end verification and one-click promotion

.PHONY: help baseline-from-snapshot court-from-snapshot verify-bundles test test-micro dev-smoke clean write-snapshot verify-snapshot capture-once capture-daemon coverage-report s3-lifecycle daily-health-report

help:
	@echo "ACD Monitor Backend Operations"
	@echo "============================="
	@echo ""
	@echo "Available targets:"
	@echo "  baseline-from-snapshot SNAPSHOT=path  - Build baseline evidence from snapshot"
	@echo "  court-from-snapshot SNAPSHOT=path      - Build court evidence from snapshot"
	@echo "  verify-bundles                        - Check sentinel JSON keys & coverage"
	@echo "  test                                  - Run unit tests"
	@echo "  test-micro                            - Run micro tests only (fast)"
	@echo "  dev-smoke                             - Fast developer feedback loop (<10s)"
	@echo "  write-snapshot                        - Write snapshot to S3"
	@echo "  verify-snapshot                       - Verify snapshot in S3"
	@echo "  capture-once                          - Capture single 30m window"
	@echo "  capture-daemon                        - Run continuous capture daemon"
	@echo "  coverage-report                       - Generate venue coverage report"
	@echo "  s3-lifecycle                          - Configure S3 lifecycle policies"
	@echo "  daily-health-report                   - Generate daily health report"
	@echo "  clean                                 - Clean temporary files"
	@echo ""
	@echo "Examples:"
	@echo "  make baseline-from-snapshot SNAPSHOT=baselines/2s"
	@echo "  make court-from-snapshot SNAPSHOT=court/1s"
	@echo "  make write-snapshot SYMBOL=BTC-USD DATE=20250928 SPAN=0200-0230"
	@echo "  make verify-snapshot SYMBOL=BTC-USD DATE=20250928 SPAN=0200-0230"
	@echo "  make capture-once SYMBOL=BTC-USD START=2025-09-28T10:00:00Z END=2025-09-28T10:30:00Z"
	@echo "  make capture-daemon SYMBOLS=BTC-USD,ETH-USD"
	@echo "  make coverage-report SYMBOLS=BTC-USD,ETH-USD"
	@echo "  make s3-lifecycle --estimate-costs"
	@echo "  make daily-health-report SYMBOLS=BTC-USD,ETH-USD"

baseline-from-snapshot:
	@if [ -z "$(SNAPSHOT)" ]; then \
	echo "Error: SNAPSHOT path required"; \
	echo "Usage: make baseline-from-snapshot SNAPSHOT=baselines/2s"; \
	exit 1; \
	fi
	@echo "[MAKE:baseline] Building baseline evidence from $(SNAPSHOT)"
	@python scripts/build_research_baseline_2s.py \
	--export-dir $(SNAPSHOT)/evidence \
	--verbose
	@python scripts/generate_provenance.py \
	--snapshot $(SNAPSHOT) \
	--permutes 1000 \
	--alpha 0.05 \
	--gg-blend-alpha 0.7
	@echo "[MAKE:baseline] Baseline evidence built successfully"

court-from-snapshot:
	@if [ -z "$(SNAPSHOT)" ]; then \
	echo "Error: SNAPSHOT path required"; \
	echo "Usage: make court-from-snapshot SNAPSHOT=court/1s"; \
	exit 1; \
	fi
	@echo "[MAKE:court] Building court evidence from $(SNAPSHOT)"
	@python scripts/build_court_bundle_from_snapshot.py \
	--snapshot $(SNAPSHOT) \
	--export-dir $(SNAPSHOT)/evidence \
	--permutes 5000 \
	--alpha 0.05 \
	--no-stitch \
	--all5 \
	--verbose
	@python scripts/generate_provenance.py \
	--snapshot $(SNAPSHOT) \
	--permutes 5000 \
	--alpha 0.05 \
	--gg-blend-alpha 0.7
	@echo "[MAKE:court] Court evidence built successfully"

verify-bundles:
	@echo "[MAKE:verify] Checking bundle sentinels and coverage"
	@python3 -c "\
import json, sys, glob, pathlib; \
from datetime import datetime; \
required_files = ['leadlag_results.json', 'spread_results.json', 'info_share_results.json', 'EVIDENCE.md', 'MANIFEST.json']; \
evidence_dirs = []; \
[evidence_dirs.extend(glob.glob(pattern)) for pattern in ['baselines/*/evidence', 'court/*/evidence']]; \
print('[VERIFY:pass] All bundles verified successfully') if evidence_dirs else sys.exit(2)"

test:
	@echo "[MAKE:test] Running unit tests"
	@python -m pytest tests/ -v --tb=short

test-micro:
	@echo "[MAKE:test-micro] Running micro tests only"
	@python -m pytest -m micro -q

dev-smoke:
	@echo "[MAKE:dev-smoke] Fast developer feedback loop"
	@python -m pytest -m micro -q --maxfail=1 -x
	@echo "[MAKE:dev-smoke] Verifying bundles..."
	@python3 -c "\
import json, sys, glob, pathlib; \
evidence_dirs = []; \
[evidence_dirs.extend(glob.glob(pattern)) for pattern in ['baselines/*/evidence', 'court/*/evidence']]; \
print('[DEV-SMOKE:PASS] Bundles verified') if evidence_dirs else sys.exit(2)"

clean:
	@echo "[MAKE:clean] Cleaning temporary files"
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true

# S3 Snapshot targets
SYMBOL ?= BTC-USD
DATE   ?= 20250928
SPAN   ?= 0200-0230
OVERLAP := s3://$(ACD_S3_BUCKET)/$(ACD_S3_PREFIX)/$(SYMBOL)/$(DATE)/$(SPAN)/OVERLAP.json

write-snapshot:
	@echo "[MAKE:write-snapshot] Writing snapshot to S3..."
	@python scripts/snapshots/write_snapshot.py \
	  --bucket $$ACD_S3_BUCKET --prefix $$ACD_S3_PREFIX \
	  --symbol $(SYMBOL) --date $(shell echo $(DATE) | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\1-\2-\3/') --start-time $(shell echo $(SPAN) | cut -d- -f1) --end-time $(shell echo $(SPAN) | cut -d- -f2) --venues binance,coinbase

verify-snapshot:
	@echo "[MAKE:verify-snapshot] Verifying snapshot..."
	@python scripts/snapshots/verify_snapshot.py --overlap "$(OVERLAP)"

# Continuous capture targets
capture-once:
	@if [ -z "$(SYMBOL)" ] || [ -z "$(START)" ] || [ -z "$(END)" ]; then \
	echo "Error: SYMBOL, START, and END required"; \
	echo "Usage: make capture-once SYMBOL=BTC-USD START=2025-09-28T10:00:00Z END=2025-09-28T10:30:00Z"; \
	exit 1; \
	fi
	@echo "[MAKE:capture-once] Capturing single window with enhanced WebSocket support..."
	@python scripts/capture/capture_window_enhanced.py \
	  --symbol $(SYMBOL) \
	  --start $(START) \
	  --end $(END) \
	  --venues binance,coinbase,kraken,okx,bybit \
	  --bucket $(ACD_S3_BUCKET) \
	  --prefix $(ACD_S3_PREFIX) \
	  --verbose

capture-daemon:
	@if [ -z "$(SYMBOLS)" ]; then \
	echo "Error: SYMBOLS required"; \
	echo "Usage: make capture-daemon SYMBOLS=BTC-USD,ETH-USD"; \
	exit 1; \
	fi
	@echo "[MAKE:capture-daemon] Starting continuous capture daemon..."
	@python scripts/capture/roll_capture.py \
	  --symbols $(SYMBOLS) \
	  --venues binance,coinbase,kraken,okx,bybit \
	  --bucket $(ACD_S3_BUCKET) \
	  --prefix $(ACD_S3_PREFIX) \
	  --verbose

coverage-report:
	@if [ -z "$(SYMBOLS)" ]; then \
	echo "Error: SYMBOLS required"; \
	echo "Usage: make coverage-report SYMBOLS=BTC-USD,ETH-USD"; \
	exit 1; \
	fi
	@echo "[MAKE:coverage-report] Generating venue coverage report..."
	@python scripts/capture/coverage_monitor.py \
	  --symbols $(SYMBOLS) \
	  --days-back 1 \
	  --bucket acd-monitor-snapshots \
	  --prefix snapshots \
	  --output reports/coverage_report.json \
	  --verbose

s3-lifecycle:
	@echo "[MAKE:s3-lifecycle] Configuring S3 lifecycle policies..."
	@python scripts/capture/s3_lifecycle_config.py \
	  --bucket acd-monitor-snapshots \
	  --prefix snapshots \
	  --estimate-costs \
	  --verbose

daily-health-report:
	@if [ -z "$(SYMBOLS)" ]; then \
	echo "Error: SYMBOLS required"; \
	echo "Usage: make daily-health-report SYMBOLS=BTC-USD,ETH-USD"; \
	exit 1; \
	fi
	@echo "[MAKE:daily-health-report] Generating daily health report..."
	@python scripts/ops/daily_health_report.py \
	  --symbols $(SYMBOLS) \
	  --days-back 1 \
	  --bucket acd-monitor-snapshots \
	  --prefix snapshots \
	  --output reports/daily_status.json \
	  --verbose
