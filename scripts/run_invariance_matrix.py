#!/usr/bin/env python3
"""
ACD Invariance Matrix Analysis Script

This script runs the invariance matrix analysis to determine whether venue
leadership is invariant across different market environments (volatility, 
funding, liquidity regimes).

Usage:
    python scripts/run_invariance_matrix.py \
      --vol exports/leadership_by_day.csv \
      --fund exports/leadership_by_day_funding.csv \
      --liq exports/leadership_by_day_liquidity.csv \
      --export-dir exports --verbose

Optional:
    --start 2025-01-01 --end 2025-09-24
    --print-evidence
"""

import sys
import os
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from acd.analytics.invariance_matrix import InvarianceMatrixAnalyzer, create_invariance_analyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InvarianceMatrixRunner:
    """
    Runner class for invariance matrix analysis.
    """
    
    def __init__(self):
        self.analyzer = create_invariance_analyzer()
        
    def run_analysis(
        self,
        volatility_file: str,
        funding_file: str,
        liquidity_file: str,
        export_dir: str = "exports",
        start_date: str = "2025-01-01",
        end_date: str = "2025-09-24",
        print_evidence: bool = False
    ) -> Dict[str, Any]:
        """
        Run complete invariance matrix analysis.
        
        Args:
            volatility_file: Path to volatility leadership CSV
            funding_file: Path to funding leadership CSV
            liquidity_file: Path to liquidity leadership CSV
            export_dir: Output directory
            start_date: Start date string
            end_date: End date string
            print_evidence: Whether to print evidence blocks
            
        Returns:
            Analysis results dictionary
        """
        logger.info("Starting ACD Invariance Matrix analysis")
        
        # Run analysis
        result = self.analyzer.analyze_invariance(
            volatility_file=volatility_file,
            funding_file=funding_file,
            liquidity_file=liquidity_file,
            output_dir=export_dir,
            start_date=start_date,
            end_date=end_date
        )
        
        # Create summary
        summary = {
            "timestamp": datetime.now().isoformat(),
            "parameters": {
                "volatility_file": volatility_file,
                "funding_file": funding_file,
                "liquidity_file": liquidity_file,
                "start_date": start_date,
                "end_date": end_date,
                "export_dir": export_dir
            },
            "results": {
                "venues_analyzed": len(result.matrix_df),
                "environments": 3,
                "regimes_per_env": 3,
                "total_bins": 9,
                "guardrails": len(result.guardrails),
                "matrix_shape": result.matrix_df.shape
            },
            "export_files": [
                "invariance_matrix.csv",
                "invariance_report.json",
                "invariance_summary.md",
                "MANIFEST.json"
            ]
        }
        
        # Print evidence if requested
        if print_evidence:
            self._print_evidence_blocks(export_dir)
        
        return summary
    
    def _print_evidence_blocks(self, export_dir: str) -> None:
        """Print evidence blocks for verification."""
        print("\n" + "="*80)
        print("ACD INVARIANCE MATRIX EVIDENCE BLOCKS")
        print("="*80)
        
        # File list
        print("-----BEGIN INVARIANCE FILES-----")
        import subprocess
        try:
            result = subprocess.run(
                ["ls", "-lh", export_dir],
                capture_output=True, text=True, check=True
            )
            for line in result.stdout.strip().split('\n'):
                print(f"  {line}")
        except subprocess.CalledProcessError:
            print("  Error listing files")
        print("-----END INVARIANCE FILES-----")
        
        # Matrix CSV (top 10 lines)
        print("-----BEGIN INVARIANCE MATRIX (top)-----")
        try:
            result = subprocess.run(
                ["head", "-n", "10", os.path.join(export_dir, "invariance_matrix.csv")],
                capture_output=True, text=True, check=True
            )
            print(result.stdout)
        except subprocess.CalledProcessError:
            print("Error reading matrix CSV")
        print("-----END INVARIANCE MATRIX (top)-----")
        
        # Report JSON
        print("-----BEGIN INVARIANCE REPORT-----")
        try:
            with open(os.path.join(export_dir, "invariance_report.json"), "r") as f:
                report_data = json.load(f)
            print(json.dumps(report_data, indent=2, default=str))
        except Exception as e:
            print(f"Error reading report JSON: {e}")
        print("-----END INVARIANCE REPORT-----")
        
        # Stats from logs
        print("-----BEGIN INVARIANCE STATS (grep)-----")
        try:
            # This would normally grep from log files, but for now just show the pattern
            print("Pattern: grep -E '^\\[STATS:env:(volatility|funding|liquidity|global):' /tmp/acd_invariance.log")
            print("Note: Stats are printed during analysis execution")
        except Exception as e:
            print(f"Error with stats grep: {e}")
        print("-----END INVARIANCE STATS (grep)-----")
        
        # Guardrails
        print("-----BEGIN GUARDRAILS-----")
        try:
            with open(os.path.join(export_dir, "invariance_report.json"), "r") as f:
                report_data = json.load(f)
            guardrails = report_data.get("guardrails", [])
            if guardrails:
                for guardrail in guardrails:
                    print(f"GUARDRAIL: {guardrail}")
            else:
                print("None")
        except Exception as e:
            print(f"Error reading guardrails: {e}")
        print("-----END GUARDRAILS-----")
        
        print("="*80)
    
    def save_results(self, results: Dict[str, Any], output_file: str) -> None:
        """Save analysis results to JSON file."""
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"Results saved to {output_file}")


def main():
    """Main function to run invariance matrix analysis."""
    parser = argparse.ArgumentParser(description="Run ACD Invariance Matrix analysis")
    parser.add_argument("--vol", required=True, help="Volatility leadership CSV file")
    parser.add_argument("--fund", required=True, help="Funding leadership CSV file")
    parser.add_argument("--liq", required=True, help="Liquidity leadership CSV file")
    parser.add_argument("--export-dir", default="exports", help="Export directory")
    parser.add_argument("--start", default="2025-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2025-09-24", help="End date (YYYY-MM-DD)")
    parser.add_argument("--print-evidence", action="store_true", help="Print evidence blocks")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create runner instance
    runner = InvarianceMatrixRunner()
    
    try:
        # Run analysis
        results = runner.run_analysis(
            volatility_file=args.vol,
            funding_file=args.fund,
            liquidity_file=args.liq,
            export_dir=args.export_dir,
            start_date=args.start,
            end_date=args.end,
            print_evidence=args.print_evidence
        )
        
        # Save results
        runner.save_results(results, "invariance_matrix_results.json")
        
        # Print summary
        print("\n" + "="*80)
        print("ACD INVARIANCE MATRIX ANALYSIS SUMMARY")
        print("="*80)
        print(f"Analysis period: {args.start} to {args.end}")
        print(f"Venues analyzed: {results['results']['venues_analyzed']}")
        print(f"Environment bins: {results['results']['total_bins']}")
        print(f"Guardrails triggered: {results['results']['guardrails']}")
        print(f"Export files created in: {args.export_dir}/")
        for export_file in results['export_files']:
            print(f"  - {export_file}")
        
        print("\nMatrix Shape:", results['results']['matrix_shape'])
        print("="*80)
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
