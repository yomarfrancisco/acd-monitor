#!/usr/bin/env python3
"""
Run invariance matrix analysis with CLI flags.

This script provides a command-line interface for running the ACD Invariance Matrix
analysis with configurable parameters for days, bootstrap samples, export directory,
and verbose logging.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from acd.analytics.invariance_matrix import InvarianceMatrixAnalyzer


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('invariance_matrix_analysis.log')
        ]
    )


def run_invariance_matrix_analysis(
    vol_csv: str,
    fund_csv: str,
    liq_csv: str,
    days: int,
    bootstrap: int,
    export_dir: str,
    verbose: bool = False
) -> None:
    """
    Run invariance matrix analysis with specified parameters.
    
    Args:
        vol_csv: Path to volatility leadership CSV
        fund_csv: Path to funding leadership CSV  
        liq_csv: Path to liquidity leadership CSV
        days: Number of days to analyze
        bootstrap: Number of bootstrap samples
        export_dir: Export directory for results
        verbose: Verbose logging
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting invariance matrix analysis")
    
    # Create analyzer
    analyzer = InvarianceMatrixAnalyzer()
    
    # Run analysis
    try:
        logger.info(f"Running invariance analysis on {vol_csv}, {fund_csv}, {liq_csv}")
        results = analyzer.analyze_invariance(
            volatility_file=vol_csv,
            funding_file=fund_csv,
            liquidity_file=liq_csv,
            output_dir=export_dir,
            start_date="2025-07-31",
            end_date="2025-09-27"
        )
        
        if results:
            logger.info("Invariance matrix analysis completed successfully")
            
            # Print evidence blocks
            print_evidence_blocks(export_dir, results)
        else:
            logger.warning("No invariance matrix results generated")
            
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)


def print_evidence_blocks(export_dir: str, results: dict) -> None:
    """Print court-ready evidence blocks."""
    print("\n" + "="*80)
    print("INVARIANCE MATRIX ANALYSIS - EVIDENCE")
    print("="*80)
    
    # Evidence Block 1: Files created
    print("\n📁 INVARIANCE FILES")
    print("-" * 40)
    try:
        import subprocess
        result = subprocess.run(['ls', '-lh', f'{export_dir}/invariance_*'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("No invariance files found")
    except Exception as e:
        print(f"Error listing files: {e}")
    
    # Evidence Block 2: Matrix summary
    print("\n📊 INVARIANCE MATRIX (top)")
    print("-" * 40)
    try:
        matrix_file = Path(export_dir) / "invariance_matrix.csv"
        if matrix_file.exists():
            import pandas as pd
            df = pd.read_csv(matrix_file)
            print("Top venues by Stability Index:")
            top_venues = df.nlargest(5, 'SI')[['venue', 'SI', 'Range', 'MinShare']]
            print(top_venues.to_string(index=False, float_format='%.4f'))
        else:
            print("No matrix file found")
    except Exception as e:
        print(f"Error reading matrix: {e}")
    
    # Evidence Block 3: Report summary
    print("\n📋 INVARIANCE REPORT")
    print("-" * 40)
    try:
        report_file = Path(export_dir) / "invariance_report.json"
        if report_file.exists():
            import json
            with open(report_file, 'r') as f:
                report = json.load(f)
            print(f"Spec Version: {report.get('specVersion', 'N/A')}")
            print(f"Code Version: {report.get('codeVersion', 'N/A')}")
            print(f"Window: {report.get('window', 'N/A')}")
            print(f"Regime Counts: {report.get('regimeCounts', 'N/A')}")
        else:
            print("No report file found")
    except Exception as e:
        print(f"Error reading report: {e}")
    
    # Evidence Block 4: Stats logs
    print("\n📈 INVARIANCE STATS (grep)")
    print("-" * 40)
    try:
        import subprocess
        result = subprocess.run(['grep', '-E', '\\[STATS:env:', 'invariance_matrix_analysis.log'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("No stats logs found")
    except Exception as e:
        print(f"Error reading stats: {e}")
    
    # Evidence Block 5: Guardrails
    print("\n⚠️ GUARDRAILS")
    print("-" * 40)
    try:
        import subprocess
        result = subprocess.run(['grep', '-E', '\\[GUARDRAIL:', 'invariance_matrix_analysis.log'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("No guardrail warnings found")
    except Exception as e:
        print(f"Error reading guardrails: {e}")
    
    print("\n" + "="*80)


def main():
    """Main function to run invariance matrix analysis."""
    parser = argparse.ArgumentParser(description="Run invariance matrix analysis")
    parser.add_argument("--vol", required=True, help="Volatility leadership CSV path")
    parser.add_argument("--fund", required=True, help="Funding leadership CSV path")
    parser.add_argument("--liq", required=True, help="Liquidity leadership CSV path")
    parser.add_argument("--days", type=int, default=30, help="Number of days to analyze")
    parser.add_argument("--bootstrap", type=int, default=500, help="Number of bootstrap samples")
    parser.add_argument("--export-dir", default="exports", help="Export directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Create export directory
    Path(args.export_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        # Run analysis
        run_invariance_matrix_analysis(
            vol_csv=args.vol,
            fund_csv=args.fund,
            liq_csv=args.liq,
            days=args.days,
            bootstrap=args.bootstrap,
            export_dir=args.export_dir,
            verbose=args.verbose
        )
        
    except Exception as e:
        logging.error(f"Analysis failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
