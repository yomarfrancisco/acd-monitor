# ACD Monitor - Backend Operations
# End-to-end verification and one-click promotion

.PHONY: help baseline-from-snapshot court-from-snapshot verify-bundles test clean

help:
	@echo "ACD Monitor Backend Operations"
	@echo "============================="
	@echo ""
	@echo "Available targets:"
	@echo "  baseline-from-snapshot SNAPSHOT=path  - Build baseline evidence from snapshot"
	@echo "  court-from-snapshot SNAPSHOT=path      - Build court evidence from snapshot"
	@echo "  verify-bundles                        - Check sentinel JSON keys & coverage"
	@echo "  test                                  - Run unit tests"
	@echo "  clean                                 - Clean temporary files"
	@echo ""
	@echo "Examples:"
	@echo "  make baseline-from-snapshot SNAPSHOT=baselines/2s"
	@echo "  make court-from-snapshot SNAPSHOT=court/1s"

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
	@python - <<'PY'
	import json, sys, glob, pathlib
	from datetime import datetime

	# Check for required evidence files
	required_files = [
	    "leadlag_results.json",
	    "spread_results.json", 
	    "info_share_results.json",
	    "EVIDENCE.md",
	    "MANIFEST.json"
	]

	# Find evidence directories
	evidence_dirs = []
	for pattern in ["baselines/*/evidence", "court/*/evidence", "real_data_runs/*/evidence"]:
	    evidence_dirs.extend(glob.glob(pattern))

	if not evidence_dirs:
	    print("[ABORT:verify] No evidence directories found")
	    sys.exit(2)

	for evidence_dir in evidence_dirs:
	    print(f"[VERIFY:check] {evidence_dir}")
	    
	    # Check required files exist
	    missing_files = []
	    for file in required_files:
	        if not pathlib.Path(evidence_dir, file).exists():
	            missing_files.append(file)
	    
	    if missing_files:
	        print(f"[ABORT:verify] Missing files in {evidence_dir}: {missing_files}")
	        sys.exit(2)
	    
	    # Check leadlag_results.json has edges
	    try:
	        with open(pathlib.Path(evidence_dir, "leadlag_results.json")) as f:
	            leadlag = json.load(f)
	        if not leadlag.get("edges") or len(leadlag["edges"]) == 0:
	            print(f"[ABORT:verify] Empty edges in {evidence_dir}/leadlag_results.json")
	            sys.exit(2)
	        print(f"[VERIFY:leadlag] {len(leadlag['edges'])} edges found")
	    except Exception as e:
	        print(f"[ABORT:verify] Error reading leadlag_results.json: {e}")
	        sys.exit(2)
	    
	    # Check spread_results.json has permutes
	    try:
	        with open(pathlib.Path(evidence_dir, "spread_results.json")) as f:
	            spread = json.load(f)
	        if spread.get("permutes", 0) < 1000:
	            print(f"[ABORT:verify] Insufficient permutations in {evidence_dir}/spread_results.json")
	            sys.exit(2)
	        print(f"[VERIFY:spread] {spread.get('permutes', 0)} permutations found")
	    except Exception as e:
	        print(f"[ABORT:verify] Error reading spread_results.json: {e}")
	        sys.exit(2)
	    
	    # Check info_share_results.json has bounds
	    try:
	        with open(pathlib.Path(evidence_dir, "info_share_results.json")) as f:
	            infoshare = json.load(f)
	        if not infoshare.get("bounds") or len(infoshare["bounds"]) == 0:
	            print(f"[ABORT:verify] Empty bounds in {evidence_dir}/info_share_results.json")
	            sys.exit(2)
	        print(f"[VERIFY:infoshare] {len(infoshare['bounds'])} venue bounds found")
	    except Exception as e:
	        print(f"[ABORT:verify] Error reading info_share_results.json: {e}")
	        sys.exit(2)

	print("[VERIFY:pass] All bundles verified successfully")
	PY

test:
	@echo "[MAKE:test] Running unit tests"
	@python -m pytest tests/ -v --tb=short

clean:
	@echo "[MAKE:clean] Cleaning temporary files"
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
