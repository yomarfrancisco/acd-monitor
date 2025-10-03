#!/usr/bin/env python3
"""
Reporting v2: Attribution Tables and Structured Outputs
========================================================

This module implements regulatory-ready reporting with:
1. Attribution tables showing driver breakdown
2. Structured JSON + PDF outputs
3. Regulatory-compliant formatting
4. Comprehensive documentation and provenance
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import logging
from dataclasses import dataclass, asdict
import matplotlib.pyplot as plt
import seaborn as sns

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AttributionEntry:
    """Single attribution entry for a driver."""

    driver_name: str
    driver_type: str  # 'venue', 'session', 'shock', 'structure'
    contribution: float
    confidence: float
    evidence: List[str]
    methodology: str


@dataclass
class AttributionTable:
    """Complete attribution table for a time period."""

    period_start: datetime
    period_end: datetime
    total_coordination_score: float
    attribution_entries: List[AttributionEntry]
    methodology_summary: str
    data_quality_score: float


class ReportingV2:
    """Reporting v2 system with attribution tables and structured outputs."""

    def __init__(self, output_dir: str = "analysis/reporting_v2"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Reporting templates and configurations
        self.templates = {
            "regulatory_summary": self._create_regulatory_summary_template(),
            "attribution_table": self._create_attribution_table_template(),
            "methodology_section": self._create_methodology_section_template(),
        }

    def _create_regulatory_summary_template(self) -> str:
        """Create regulatory summary template."""
        return """
# ACD Analysis Report: Coordination Assessment

**Report ID**: {report_id}
**Analysis Period**: {period_start} to {period_end}
**Generated**: {generation_date}
**Methodology**: Algorithmic Competition Detection (ACD) v2.0

## Executive Summary

**Overall Assessment**: {overall_assessment}
**Confidence Level**: {confidence_level}
**Coordination Score**: {coordination_score}/100

### Key Findings
{key_findings}

### Regulatory Implications
{regulatory_implications}

## Attribution Analysis

The following table shows the breakdown of coordination drivers:

{attribution_table}

## Methodology

{methodology_section}

## Data Quality Assessment

{data_quality_section}

## Appendices

{appendices}
"""

    def _create_attribution_table_template(self) -> str:
        """Create attribution table template."""
        return """
| Driver | Type | Contribution | Confidence | Evidence | Methodology |
|--------|------|-------------|------------|----------|-------------|
{attribution_rows}
"""

    def _create_methodology_section_template(self) -> str:
        """Create methodology section template."""
        return """
### ACD Methodology Overview

The Algorithmic Competition Detection (ACD) methodology employs a multi-layered approach:

1. **Wave-1 Analysis**: Basic statistical tests and correlation analysis
2. **Wave-2 Analysis**: Advanced econometric tests (Granger causality, cointegration, event studies)
3. **Wave-3 Analysis**: Machine learning approaches (ICP, VMM, copula analysis, clustering)

### Attribution Methodology

Attribution is calculated using:
- **ICP Analysis**: Environment-dependent relationship analysis
- **VMM Analysis**: Model comparison for competitive vs coordination dynamics
- **Copula Analysis**: Dependence structure analysis
- **Clustering Analysis**: Regime identification and coordination pattern detection

### Confidence Scoring

Confidence scores are based on:
- Statistical significance of results
- Consistency across multiple methodologies
- Data quality and completeness
- Sample size adequacy
"""

    def create_attribution_table(
        self, analysis_results: Dict[str, Any], period_start: datetime, period_end: datetime
    ) -> AttributionTable:
        """Create attribution table from analysis results."""
        logger.info("Creating attribution table...")

        attribution_entries = []

        # Extract coordination score
        coordination_score = analysis_results.get("composite_index", {}).get("overall_score", 0)

        # Venue attribution (from Wave-2 and Wave-3 results)
        if "granger" in analysis_results:
            granger_results = analysis_results["granger"]
            for venue, contribution in granger_results.get("venue_contributions", {}).items():
                attribution_entries.append(
                    AttributionEntry(
                        driver_name=f"Venue {venue}",
                        driver_type="venue",
                        contribution=contribution,
                        confidence=granger_results.get("confidence", 0.5),
                        evidence=["Granger causality analysis"],
                        methodology="Wave-2 Granger Causality",
                    )
                )

        # Session attribution (from environment analysis)
        if "session_analysis" in analysis_results:
            session_results = analysis_results["session_analysis"]
            for session, contribution in session_results.get("session_contributions", {}).items():
                attribution_entries.append(
                    AttributionEntry(
                        driver_name=f"Session {session}",
                        driver_type="session",
                        contribution=contribution,
                        confidence=session_results.get("confidence", 0.5),
                        evidence=["Session-based analysis"],
                        methodology="Environment Analysis",
                    )
                )

        # Shock attribution (from event studies)
        if "event_study" in analysis_results:
            event_results = analysis_results["event_study"]
            for shock_type, contribution in event_results.get("shock_contributions", {}).items():
                attribution_entries.append(
                    AttributionEntry(
                        driver_name=f"Shock {shock_type}",
                        driver_type="shock",
                        contribution=contribution,
                        confidence=event_results.get("confidence", 0.5),
                        evidence=["Event study analysis"],
                        methodology="Wave-2 Event Studies",
                    )
                )

        # Structure attribution (from market structure analysis)
        if "market_structure" in analysis_results:
            structure_results = analysis_results["market_structure"]
            for structure_type, contribution in structure_results.get(
                "structure_contributions", {}
            ).items():
                attribution_entries.append(
                    AttributionEntry(
                        driver_name=f"Structure {structure_type}",
                        driver_type="structure",
                        contribution=contribution,
                        confidence=structure_results.get("confidence", 0.5),
                        evidence=["Market structure analysis"],
                        methodology="Wave-2 Market Structure",
                    )
                )

        # Calculate data quality score
        data_quality_score = self._calculate_data_quality_score(analysis_results)

        attribution_table = AttributionTable(
            period_start=period_start,
            period_end=period_end,
            total_coordination_score=coordination_score,
            attribution_entries=attribution_entries,
            methodology_summary="ACD v2.0 Multi-layered Analysis",
            data_quality_score=data_quality_score,
        )

        logger.info(f"Created attribution table with {len(attribution_entries)} entries")
        return attribution_table

    def _calculate_data_quality_score(self, analysis_results: Dict[str, Any]) -> float:
        """Calculate data quality score from analysis results."""
        quality_factors = []

        # Check for missing data
        if "data_quality" in analysis_results:
            data_quality = analysis_results["data_quality"]
            missing_ratio = data_quality.get("missing_data_ratio", 0)
            quality_factors.append(1 - missing_ratio)

        # Check for sample size adequacy
        if "sample_size" in analysis_results:
            sample_size = analysis_results["sample_size"]
            if sample_size > 10000:
                quality_factors.append(1.0)
            elif sample_size > 5000:
                quality_factors.append(0.8)
            elif sample_size > 1000:
                quality_factors.append(0.6)
            else:
                quality_factors.append(0.4)

        # Check for methodology coverage
        methodology_count = 0
        expected_methodologies = ["wave1", "wave2", "wave3"]
        for method in expected_methodologies:
            if method in analysis_results:
                methodology_count += 1

        quality_factors.append(methodology_count / len(expected_methodologies))

        return np.mean(quality_factors) if quality_factors else 0.5

    def generate_attribution_visualization(self, attribution_table: AttributionTable) -> None:
        """Generate visualization for attribution table."""
        logger.info("Generating attribution visualization...")

        # Create attribution plot
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

        # Driver type breakdown
        driver_types = {}
        for entry in attribution_table.attribution_entries:
            if entry.driver_type not in driver_types:
                driver_types[entry.driver_type] = 0
            driver_types[entry.driver_type] += entry.contribution

        ax1.pie(driver_types.values(), labels=driver_types.keys(), autopct="%1.1f%%")
        ax1.set_title("Coordination Attribution by Driver Type")

        # Top contributors
        sorted_entries = sorted(
            attribution_table.attribution_entries, key=lambda x: x.contribution, reverse=True
        )[:10]

        contributors = [entry.driver_name for entry in sorted_entries]
        contributions = [entry.contribution for entry in sorted_entries]

        ax2.barh(contributors, contributions)
        ax2.set_title("Top 10 Coordination Drivers")
        ax2.set_xlabel("Contribution Score")

        plt.tight_layout()
        plt.savefig(self.output_dir / "attribution_analysis.png", dpi=300, bbox_inches="tight")
        plt.close()

        logger.info("Attribution visualization saved")

    def generate_regulatory_report(
        self, attribution_table: AttributionTable, analysis_results: Dict[str, Any]
    ) -> str:
        """Generate regulatory-compliant report."""
        logger.info("Generating regulatory report...")

        # Calculate overall assessment
        coordination_score = attribution_table.total_coordination_score
        if coordination_score > 70:
            overall_assessment = "High Coordination Risk"
            confidence_level = "High"
        elif coordination_score > 40:
            overall_assessment = "Moderate Coordination Risk"
            confidence_level = "Medium"
        else:
            overall_assessment = "Low Coordination Risk"
            confidence_level = "Low"

        # Generate key findings
        key_findings = self._generate_key_findings(attribution_table, analysis_results)

        # Generate regulatory implications
        regulatory_implications = self._generate_regulatory_implications(
            overall_assessment, coordination_score
        )

        # Create attribution table rows
        attribution_rows = []
        for entry in attribution_table.attribution_entries:
            attribution_rows.append(
                f"| {entry.driver_name} | {entry.driver_type} | {entry.contribution:.2f} | "
                f"{entry.confidence:.2f} | {', '.join(entry.evidence)} | {entry.methodology} |"
            )

        # Generate report
        report_id = f"ACD-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        report = self.templates["regulatory_summary"].format(
            report_id=report_id,
            period_start=attribution_table.period_start.strftime("%Y-%m-%d %H:%M:%S"),
            period_end=attribution_table.period_end.strftime("%Y-%m-%d %H:%M:%S"),
            generation_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            overall_assessment=overall_assessment,
            confidence_level=confidence_level,
            coordination_score=coordination_score,
            key_findings=key_findings,
            regulatory_implications=regulatory_implications,
            attribution_table=self.templates["attribution_table"].format(
                attribution_rows="\n".join(attribution_rows)
            ),
            methodology_section=self.templates["methodology_section"],
            data_quality_section=f"Data Quality Score: {attribution_table.data_quality_score:.2f}/1.0",
            appendices="See detailed analysis results in JSON format.",
        )

        return report

    def _generate_key_findings(
        self, attribution_table: AttributionTable, analysis_results: Dict[str, Any]
    ) -> str:
        """Generate key findings section."""
        findings = []

        # Top coordination drivers
        top_drivers = sorted(
            attribution_table.attribution_entries, key=lambda x: x.contribution, reverse=True
        )[:3]

        findings.append(f"**Top Coordination Drivers:**")
        for i, driver in enumerate(top_drivers, 1):
            findings.append(
                f"{i}. {driver.driver_name} ({driver.driver_type}): {driver.contribution:.2f} contribution"
            )

        # Methodology results
        if "wave2" in analysis_results:
            findings.append(
                f"**Wave-2 Analysis:** {len(analysis_results['wave2'])} econometric tests completed"
            )

        if "wave3" in analysis_results:
            findings.append(
                f"**Wave-3 Analysis:** {len(analysis_results['wave3'])} advanced methods applied"
            )

        # Data quality
        findings.append(f"**Data Quality:** {attribution_table.data_quality_score:.2f}/1.0 score")

        return "\n".join(findings)

    def _generate_regulatory_implications(
        self, overall_assessment: str, coordination_score: float
    ) -> str:
        """Generate regulatory implications section."""
        implications = []

        if coordination_score > 70:
            implications.append("**High Priority:** Immediate regulatory attention recommended")
            implications.append("**Actions:** Consider market intervention or investigation")
            implications.append("**Monitoring:** Enhanced surveillance required")
        elif coordination_score > 40:
            implications.append("**Medium Priority:** Continued monitoring recommended")
            implications.append("**Actions:** Regular review and assessment")
            implications.append("**Monitoring:** Standard surveillance sufficient")
        else:
            implications.append("**Low Priority:** Routine monitoring adequate")
            implications.append("**Actions:** Standard market oversight")
            implications.append("**Monitoring:** Baseline surveillance sufficient")

        return "\n".join(implications)

    def save_structured_outputs(
        self,
        attribution_table: AttributionTable,
        analysis_results: Dict[str, Any],
        regulatory_report: str,
    ) -> None:
        """Save structured outputs (JSON + PDF-ready)."""
        logger.info("Saving structured outputs...")

        # Save JSON outputs
        json_output = {
            "report_metadata": {
                "generation_date": datetime.now().isoformat(),
                "period_start": attribution_table.period_start.isoformat(),
                "period_end": attribution_table.period_end.isoformat(),
                "methodology_version": "ACD v2.0",
                "data_quality_score": attribution_table.data_quality_score,
            },
            "attribution_table": {
                "total_coordination_score": attribution_table.total_coordination_score,
                "entries": [asdict(entry) for entry in attribution_table.attribution_entries],
            },
            "analysis_results": analysis_results,
            "regulatory_report": regulatory_report,
        }

        with open(self.output_dir / "acd_report.json", "w") as f:
            json.dump(json_output, f, indent=2, default=str)

        # Save markdown report
        with open(self.output_dir / "acd_report.md", "w") as f:
            f.write(regulatory_report)

        # Save attribution table CSV
        attribution_df = pd.DataFrame(
            [asdict(entry) for entry in attribution_table.attribution_entries]
        )
        attribution_df.to_csv(self.output_dir / "attribution_table.csv", index=False)

        logger.info(f"Structured outputs saved to {self.output_dir}")

    def run_reporting_pipeline(
        self, analysis_results: Dict[str, Any], period_start: datetime, period_end: datetime
    ) -> None:
        """Run complete reporting pipeline."""
        logger.info("Starting Reporting v2 pipeline...")

        # Create attribution table
        attribution_table = self.create_attribution_table(
            analysis_results, period_start, period_end
        )

        # Generate visualization
        self.generate_attribution_visualization(attribution_table)

        # Generate regulatory report
        regulatory_report = self.generate_regulatory_report(attribution_table, analysis_results)

        # Save structured outputs
        self.save_structured_outputs(attribution_table, analysis_results, regulatory_report)

        logger.info("Reporting v2 pipeline complete!")


def main():
    """Main execution function."""
    # Example usage
    reporting = ReportingV2()

    # Mock analysis results for testing
    mock_results = {
        "composite_index": {"overall_score": 65.5},
        "granger": {
            "venue_contributions": {"binance": 0.3, "coinbase": 0.25, "kraken": 0.2},
            "confidence": 0.8,
        },
        "session_analysis": {
            "session_contributions": {"asia": 0.15, "europe": 0.2, "us": 0.1},
            "confidence": 0.7,
        },
        "event_study": {
            "shock_contributions": {"price_shock": 0.1, "volume_shock": 0.05},
            "confidence": 0.6,
        },
        "market_structure": {
            "structure_contributions": {"volatility": 0.1, "trend": 0.05},
            "confidence": 0.5,
        },
        "data_quality": {"missing_data_ratio": 0.05},
        "sample_size": 15000,
    }

    period_start = datetime(2025, 9, 1)
    period_end = datetime(2025, 9, 30)

    reporting.run_reporting_pipeline(mock_results, period_start, period_end)


if __name__ == "__main__":
    main()
