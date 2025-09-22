"""
Offline Mock Provider - Deterministic responses for testing

This module provides an offline fallback provider that generates
deterministic, templated responses using ACD artifacts and fixtures.
It's designed for testing and fallback scenarios when Chatbase is unavailable.
"""

import os
import json
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import logging

from .chatbase_adapter import AgentMessage, Health

logger = logging.getLogger(__name__)


@dataclass
class MockResponseTemplate:
    """Template for mock responses"""

    intent: str
    pattern: str
    template: str
    requires_artifacts: List[str]


class OfflineMockProvider:
    """
    Offline mock provider with deterministic responses

    This provider generates templated responses based on query patterns
    and available ACD artifacts. It's designed for testing and fallback.
    """

    def __init__(self, artifacts_dir: str = "artifacts"):
        self.artifacts_dir = Path(artifacts_dir)
        self.templates = self._load_response_templates()
        self.fixtures = self._load_fixtures()

        logger.info(f"OfflineMockProvider initialized with {len(self.templates)} templates")

    def generate(
        self,
        *,
        prompt: str,
        tools: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AgentMessage:
        """
        Generate mock response based on prompt patterns

        Args:
            prompt: User message content
            tools: Available tools (not used in mock)
            context: Additional context (not used in mock)
            stream: Whether to use streaming (not supported in mock)
            session_id: Session identifier
            user_id: User identifier

        Returns:
            AgentMessage with templated response
        """
        try:
            # Detect intent from prompt
            intent = self._detect_intent(prompt)

            # Get template for intent
            template = self.templates.get(intent, self.templates["default"])

            # Load relevant artifacts
            artifacts = self._load_relevant_artifacts(template.requires_artifacts)

            # Generate response using template
            content = self._render_template(template, prompt, artifacts)

            # Generate session ID if not provided
            if not session_id:
                session_id = f"mock_{hash(prompt) % 10000}"

            return AgentMessage(
                content=content,
                session_id=session_id,
                usage={
                    "mode": "offline_mock",
                    "intent": intent,
                    "template": template.intent,
                    "artifacts_used": list(artifacts.keys()),
                },
                metadata={
                    "provider": "offline_mock",
                    "intent": intent,
                    "artifacts_available": len(artifacts),
                    "stream": stream,
                },
            )

        except Exception as e:
            logger.error(f"Mock generation error: {e}")
            return self._get_error_response(prompt, session_id, str(e))

    def healthcheck(self) -> Health:
        """
        Check offline provider health

        Returns:
            Health status with details
        """
        try:
            # Check if artifacts directory exists
            artifacts_available = self.artifacts_dir.exists()

            # Count available templates
            template_count = len(self.templates)

            # Check for recent artifacts
            recent_artifacts = self._find_recent_artifacts()

            status = "healthy" if artifacts_available and template_count > 0 else "degraded"

            return Health(
                status=status,
                details={
                    "provider": "offline_mock",
                    "artifacts_available": artifacts_available,
                    "template_count": template_count,
                    "recent_artifacts": len(recent_artifacts),
                    "artifacts_dir": str(self.artifacts_dir),
                },
                last_check=self._get_timestamp(),
            )

        except Exception as e:
            return Health(
                status="unhealthy", details={"error": str(e)}, last_check=self._get_timestamp()
            )

    def _load_response_templates(self) -> Dict[str, MockResponseTemplate]:
        """Load response templates for different intents"""
        return {
            "risk_assessment": MockResponseTemplate(
                intent="risk_assessment",
                pattern="risk level|risk band|risk assessment|summary|verdict|low/amber/red|amber/red|assessment|screening memo",
                template="""
## Risk Assessment Summary

**Analysis Period:** {period}
**Asset Pair:** {asset_pair}

### Overall Assessment:
- **Risk Level:** {risk_level}
- **Coordination Detected:** {coordination_detected}
- **Confidence Level:** {confidence_level}

### Key Metrics:
- **Composite Score:** {composite_score}
- **ICP Contribution:** {icp_contribution}
- **VMM Contribution:** {vmm_contribution}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["integrated", "report"],
            ),
            "mirroring_analysis": MockResponseTemplate(
                intent="mirroring_analysis",
                pattern="mirroring ratio|mirroring ratios|order book|depth|cosine similarity",
                template="""
## Mirroring Analysis Results

**Analysis Period:** {period}
**Asset Pair:** {asset_pair}

### Key Metrics:
- **Mirroring Ratio:** {mirroring_ratio:.3f}
- **Coordination Score:** {coordination_score:.3f}
- **High Mirroring Pairs:** {high_mirroring_pairs}

### Interpretation:
{mirroring_interpretation}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["mirroring", "validation"],
            ),
            "alternative_explanations": MockResponseTemplate(
                intent="alternative_explanations",
                pattern="alternative explanations|which alternative|list.*alternative",
                template="""
## Alternative Explanations Analysis

**Query:** {prompt}

### Alternative Explanations Considered:
- **Arbitrage Latency:** Cross-venue latency constraints may explain apparent coordination
- **Fee Tier Structures:** VIP fee tiers and rebates can create pricing patterns
- **Inventory Shocks:** Market maker inventory needs may drive coordinated responses
- **Volatility Regimes:** High volatility periods may trigger similar risk management
- **Regulatory Events:** Market-wide regulatory announcements can cause synchronized responses

### Analysis Results:
Based on the available data, the following alternative explanations were evaluated:
- **Arbitrage Latency:** {arbitrage_analysis}
- **Fee Tier Impact:** {fee_analysis}
- **Inventory Shocks:** {inventory_analysis}
- **Volatility Controls:** {volatility_analysis}

### Conclusion:
{explanation_conclusion}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["validation"],
            ),
            "lead_lag_analysis": MockResponseTemplate(
                intent="lead_lag_analysis",
                pattern="lead|lag|leadership|persistence|granger",
                template="""
## Lead-Lag Analysis Results

**Analysis Period:** {period}
**Asset Pair:** {asset_pair}

### Leadership Metrics:
- **Switching Entropy:** {switching_entropy:.3f}
- **Significant Relationships:** {significant_relationships}
- **Persistence Scores:** {persistence_scores}

### Interpretation:
{lead_lag_interpretation}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["lead_lag", "validation"],
            ),
            "spread_floor_analysis": MockResponseTemplate(
                intent="spread_floor_analysis",
                pattern="spread floor|dwell|volatility|regime",
                template="""
## Spread Floor Analysis Results

**Analysis Period:** {period}
**Asset Pair:** {asset_pair}

### Regime Analysis:
- **Regime Stability:** {regime_stability:.3f}
- **Coordination Regime Score:** {coordination_regime_score:.3f}
- **Wide Spread Regime:** {wide_spread_regime}
- **Lockstep Regime:** {lockstep_regime}

### Interpretation:
{spread_floor_interpretation}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["hmm", "validation"],
            ),
            "icp_analysis": MockResponseTemplate(
                intent="icp_analysis",
                pattern="icp|invariance|environment|fdr",
                template="""
## ICP Invariance Analysis Results

**Analysis Period:** {period}
**Asset Pair:** {asset_pair}

### Invariance Test:
- **P-value:** {icp_p_value:.6f}
- **Power:** {power:.3f}
- **Environments:** {n_environments}
- **Environment Sizes:** {environment_sizes}

### Interpretation:
{icp_interpretation}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["icp", "validation"],
            ),
            "vmm_analysis": MockResponseTemplate(
                intent="vmm_analysis",
                pattern="vmm|over.identification|stability|moments",
                template="""
## VMM Analysis Results

**Analysis Period:** {period}
**Asset Pair:** {asset_pair}

### Over-Identification Test:
- **P-value:** {vmm_p_value:.6f}
- **Structural Stability:** {structural_stability:.3f}
- **Number of Moments:** {n_moments}
- **Convergence:** {convergence_achieved}

### Interpretation:
{vmm_interpretation}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["vmm", "validation"],
            ),
            # Crypto Exchange-Specific Templates
            "exchange_surveillance": MockResponseTemplate(
                intent="exchange_surveillance",
                pattern="spread floor|persisted|volatility|evidence pack|surveillance|flag periods",
                template="""
## Exchange Surveillance Analysis

**Analysis Period:** {period}
**Asset Pair:** {asset_pair}
**Venue:** {venue}

### Spread Floor Analysis:
- **Spread Floor Persistence:** {spread_floor_persistence:.1%}
- **Volatility During Persistence:** {volatility_during_persistence:.2%}
- **Suspicious Periods:** {suspicious_periods}
- **Risk Level:** {risk_level}

### Evidence Pack Generated:
- **Order Book Data:** {order_book_evidence}
- **Trade Data:** {trade_evidence}
- **Coordination Signals:** {coordination_evidence}
- **Provenance Hash:** {provenance_hash}

### Surveillance Recommendations:
- **Immediate Actions:** {immediate_actions}
- **Investigation Priority:** {investigation_priority}
- **Regulatory Risk:** {regulatory_risk}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["mirroring", "validation"],
            ),
            "exchange_lead_lag": MockResponseTemplate(
                intent="exchange_lead_lag",
                pattern="who led|btc/usdt|coinbase|binance|switching entropy|venue|led.*btc",
                template="""
## Exchange Lead-Lag Analysis

**Analysis Period:** {period}
**Asset Pair:** {asset_pair}
**Time Window:** {time_window}

### Venue Leadership Analysis:
- **Our Venue Leadership:** {our_venue_leadership:.1%}
- **Coinbase Leadership:** {coinbase_leadership:.1%}
- **Binance Leadership:** {binance_leadership:.1%}
- **Persistence Score:** {persistence_score:.3f}
- **Switching Entropy:** {switching_entropy:.3f}

### Leadership Patterns:
- **Dominant Leader:** {dominant_leader}
- **Leadership Stability:** {leadership_stability}
- **Suspicious Patterns:** {suspicious_patterns}

### Risk Assessment:
- **Risk Level:** {risk_level}
- **Coordination Indicators:** {coordination_indicators}
- **Investigation Required:** {investigation_required}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["lead_lag", "validation"],
            ),
            "exchange_mirroring": MockResponseTemplate(
                intent="exchange_mirroring",
                pattern="mirroring episodes|top-10 depth|external venues|arbitrage windows|depth tier|heatmap|trading hours",
                template="""
## Exchange Mirroring Analysis

**Analysis Period:** {period}
**Asset Pair:** {asset_pair}
**Depth Analysis:** Top-10 depth tiers

### Mirroring Episodes:
- **High Mirroring Episodes:** {high_mirroring_episodes}
- **Average Mirroring Ratio:** {avg_mirroring_ratio:.3f}
- **Peak Mirroring Ratio:** {peak_mirroring_ratio:.3f}
- **External Venue Correlation:** {external_venue_correlation:.3f}

### Arbitrage Windows:
- **Arbitrage Opportunities:** {arbitrage_opportunities}
- **Window Duration:** {window_duration}
- **Profit Potential:** {profit_potential}

### Depth Tier Analysis:
- **Top-3 Depth Mirroring:** {top3_depth_mirroring:.3f}
- **Mid-Depth Mirroring:** {mid_depth_mirroring:.3f}
- **Deep Book Mirroring:** {deep_book_mirroring:.3f}

### Risk Assessment:
- **Risk Level:** {risk_level}
- **Coordination Indicators:** {coordination_indicators}
- **Market Impact:** {market_impact}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["mirroring", "validation"],
            ),
            "exchange_fee_analysis": MockResponseTemplate(
                intent="exchange_fee_analysis",
                pattern="vip fee ladder|inventory shocks|signal|explain|fee tier|maker|taker",
                template="""
## Exchange Fee & Inventory Analysis

**Analysis Period:** {period}
**Asset Pair:** {asset_pair}
**Signal Date:** {signal_date}

### VIP Fee Ladder Analysis:
- **Fee Tier Structure:** {fee_tier_structure}
- **VIP Benefits:** {vip_benefits}
- **Volume Thresholds:** {volume_thresholds}
- **Fee Impact on Signal:** {fee_impact_on_signal}

### Inventory Shock Analysis:
- **Inventory Changes:** {inventory_changes}
- **Shock Magnitude:** {shock_magnitude:.2%}
- **Recovery Time:** {recovery_time}
- **Impact on Signal:** {inventory_impact_on_signal}

### Signal Explanation:
- **Primary Driver:** {primary_driver}
- **Secondary Factors:** {secondary_factors}
- **Alternative Explanations:** {alternative_explanations}
- **Confidence Level:** {confidence_level:.1%}

### Risk Assessment:
- **Risk Level:** {risk_level}
- **Regulatory Implications:** {regulatory_implications}
- **Recommended Actions:** {recommended_actions}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["validation"],
            ),
            "exchange_case_management": MockResponseTemplate(
                intent="exchange_case_management",
                pattern="case file|alert|icp/vmm|provenance hashes|case management",
                template="""
## Exchange Case Management

**Alert ID:** {alert_id}
**Case Status:** {case_status}
**Asset Pair:** {asset_pair}
**Analysis Date:** {analysis_date}

### ICP/VMM Excerpts:
- **ICP P-value:** {icp_p_value:.6f}
- **ICP Power:** {icp_power:.3f}
- **VMM P-value:** {vmm_p_value:.6f}
- **VMM Stability:** {vmm_stability:.3f}
- **Coordination Detected:** {coordination_detected}

### Provenance Hashes:
- **Data Hash:** {data_hash}
- **Analysis Hash:** {analysis_hash}
- **Case File Hash:** {case_file_hash}
- **Audit Trail:** {audit_trail}

### Case File Contents:
- **Executive Summary:** {executive_summary}
- **Technical Analysis:** {technical_analysis}
- **Evidence Files:** {evidence_files}
- **Recommendations:** {recommendations}

### Investigation Status:
- **Priority Level:** {priority_level}
- **Assigned To:** {assigned_to}
- **Due Date:** {due_date}
- **Status:** {investigation_status}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["icp", "vmm", "validation"],
            ),
            "exchange_comparison": MockResponseTemplate(
                intent="exchange_comparison",
                pattern="compare|amber period|baseline|last week|moments|validation layers|changed",
                template="""
## Exchange Period Comparison

**Analysis Period:** {analysis_period}
**Baseline Period:** {baseline_period}
**Asset Pair:** {asset_pair}

### Risk Level Comparison:
- **Current Period:** {current_risk_level}
- **Baseline Period:** {baseline_risk_level}
- **Risk Change:** {risk_change}

### Moment Changes:
- **Lead-Lag Beta:** {lead_lag_change:.3f}
- **Mirroring Ratio:** {mirroring_change:.3f}
- **Spread Floor Dwell:** {spread_floor_change:.3f}
- **Undercut Initiation:** {undercut_change}

### Validation Layer Changes:
- **Lead-Lag Validation:** {lead_lag_validation_change}
- **Mirroring Validation:** {mirroring_validation_change}
- **HMM Regime Change:** {hmm_regime_change}
- **Info-Flow Change:** {infoflow_change}

### Key Differences:
- **Primary Changes:** {primary_changes}
- **Secondary Changes:** {secondary_changes}
- **Market Conditions:** {market_conditions}
- **External Factors:** {external_factors}

### Risk Assessment:
- **Overall Risk Change:** {overall_risk_change}
- **Investigation Required:** {investigation_required}
- **Recommended Actions:** {recommended_actions}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["validation"],
            ),
            "exchange_simulation": MockResponseTemplate(
                intent="exchange_simulation",
                pattern="simulate|latency-arb|constraints|red flag|persist|stricter",
                template="""
## Exchange Simulation Analysis

**Simulation Type:** {simulation_type}
**Asset Pair:** {asset_pair}
**Analysis Period:** {period}

### Simulation Parameters:
- **Latency-Arb Constraints:** {latency_arb_constraints}
- **Stricter Thresholds:** {stricter_thresholds}
- **Simulation Duration:** {simulation_duration}

### Simulation Results:
- **Red Flag Persistence:** {red_flag_persistence}
- **Risk Level Change:** {risk_level_change}
- **Coordination Signals:** {coordination_signals}
- **False Positive Rate:** {false_positive_rate:.1%}

### Impact Analysis:
- **Market Impact:** {market_impact}
- **Trading Volume Impact:** {volume_impact:.1%}
- **Spread Impact:** {spread_impact:.3f}
- **Liquidity Impact:** {liquidity_impact}

### Recommendations:
- **Constraint Effectiveness:** {constraint_effectiveness}
- **Implementation Feasibility:** {implementation_feasibility}
- **Risk-Benefit Analysis:** {risk_benefit_analysis}
- **Next Steps:** {next_steps}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["validation"],
            ),
            "exchange_risk_summary": MockResponseTemplate(
                intent="exchange_risk_summary",
                pattern="risk bands|btc/eth|spot|ops actions|open tickets|summarize",
                template="""
## Exchange Risk Summary

**Asset Pair:** {asset_pair}
**Analysis Period:** {period}
**Risk Assessment Date:** {assessment_date}

### Risk Bands:
- **BTC/USD Risk Level:** {btc_risk_level}
- **ETH/USD Risk Level:** {eth_risk_level}
- **Overall Risk Level:** {overall_risk_level}
- **Risk Trend:** {risk_trend}

### Operations Actions Taken:
- **Surveillance Actions:** {surveillance_actions}
- **Investigation Actions:** {investigation_actions}
- **Compliance Actions:** {compliance_actions}
- **Market Actions:** {market_actions}

### Open Tickets:
- **High Priority Tickets:** {high_priority_tickets}
- **Medium Priority Tickets:** {medium_priority_tickets}
- **Low Priority Tickets:** {low_priority_tickets}
- **Total Open Tickets:** {total_open_tickets}

### Key Metrics:
- **Coordination Signals:** {coordination_signals}
- **False Positive Rate:** {false_positive_rate:.1%}
- **Investigation Success Rate:** {investigation_success_rate:.1%}
- **Average Resolution Time:** {avg_resolution_time}

### Recommendations:
- **Immediate Actions:** {immediate_actions}
- **Medium-term Actions:** {medium_term_actions}
- **Long-term Actions:** {long_term_actions}
- **Resource Requirements:** {resource_requirements}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["validation"],
            ),
            "exchange_reporting": MockResponseTemplate(
                intent="exchange_reporting",
                pattern="internal memo|cco|findings|caveats|alternative explanations|next steps|export",
                template="""
## Exchange Internal Memo

**To:** {recipient}
**From:** {sender}
**Date:** {memo_date}
**Subject:** {subject}

### Executive Summary:
{executive_summary}

### Key Findings:
- **Coordination Signals:** {coordination_signals}
- **Risk Assessment:** {risk_assessment}
- **Market Impact:** {market_impact}
- **Regulatory Implications:** {regulatory_implications}

### Caveats:
- **Data Limitations:** {data_limitations}
- **Analysis Constraints:** {analysis_constraints}
- **Uncertainty Factors:** {uncertainty_factors}
- **Assumptions Made:** {assumptions_made}

### Alternative Explanations:
- **Arbitrage Latency:** {arbitrage_latency_explanation}
- **Fee Tier Impact:** {fee_tier_explanation}
- **Inventory Shocks:** {inventory_shock_explanation}
- **Market Conditions:** {market_conditions_explanation}

### Next Steps:
- **Immediate Actions (24h):** {immediate_actions}
- **Short-term Actions (1 week):** {short_term_actions}
- **Medium-term Actions (1 month):** {medium_term_actions}
- **Long-term Actions (3 months):** {long_term_actions}

### Resource Requirements:
- **Personnel:** {personnel_requirements}
- **Technology:** {technology_requirements}
- **Budget:** {budget_requirements}
- **Timeline:** {timeline_requirements}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["validation"],
            ),
            "exchange_visualization": MockResponseTemplate(
                intent="exchange_visualization",
                pattern="heatmap|depth tier|trading hours|order-book mirroring|visualization",
                template="""
## Exchange Visualization Analysis

**Visualization Type:** {visualization_type}
**Asset Pair:** {asset_pair}
**Analysis Period:** {period}
**Trading Hours:** {trading_hours}

### Order-Book Mirroring Heatmap:
- **Depth Tier 1-3:** {depth_tier_1_3_mirroring:.3f}
- **Depth Tier 4-6:** {depth_tier_4_6_mirroring:.3f}
- **Depth Tier 7-10:** {depth_tier_7_10_mirroring:.3f}
- **Overall Mirroring:** {overall_mirroring:.3f}

### Trading Hours Analysis:
- **US Trading Hours:** {us_trading_hours_mirroring:.3f}
- **European Hours:** {european_hours_mirroring:.3f}
- **Asian Hours:** {asian_hours_mirroring:.3f}
- **Peak Mirroring Time:** {peak_mirroring_time}

### Heatmap Insights:
- **High Mirroring Periods:** {high_mirroring_periods}
- **Low Mirroring Periods:** {low_mirroring_periods}
- **Pattern Analysis:** {pattern_analysis}
- **Anomaly Detection:** {anomaly_detection}

### Risk Assessment:
- **Risk Level:** {risk_level}
- **Coordination Indicators:** {coordination_indicators}
- **Investigation Priority:** {investigation_priority}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["mirroring", "validation"],
            ),
            "exchange_market_maker": MockResponseTemplate(
                intent="exchange_market_maker",
                pattern="undercut initiation|market maker.*escalate|escalate.*repeated|undercut.*episodes",
                template="""
## Exchange Market Maker Analysis

**Analysis Period:** {period}
**Asset Pair:** {asset_pair}
**Market Maker Focus:** {market_maker_focus}

### Undercut Initiation Episodes:
- **Total Episodes:** {total_episodes}
- **Episodes by Market Maker:** {episodes_by_mm}
- **Average Undercut Size:** {avg_undercut_size:.3f}
- **Peak Undercut Size:** {peak_undercut_size:.3f}

### Market Maker Behavior:
- **Most Active MM:** {most_active_mm}
- **Highest Undercut Rate:** {highest_undercut_rate}
- **Suspicious Patterns:** {suspicious_patterns}
- **Repeat Offenders:** {repeat_offenders}

### Escalation Analysis:
- **Escalation Required:** {escalation_required}
- **Escalation Reasons:** {escalation_reasons}
- **Priority Level:** {priority_level}
- **Recommended Actions:** {recommended_actions}

### Risk Assessment:
- **Risk Level:** {risk_level}
- **Coordination Indicators:** {coordination_indicators}
- **Market Impact:** {market_impact}
- **Regulatory Risk:** {regulatory_risk}

### Investigation Status:
- **Cases Opened:** {cases_opened}
- **Cases Closed:** {cases_closed}
- **Open Investigations:** {open_investigations}
- **Resolution Rate:** {resolution_rate:.1%}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["validation"],
            ),
            "exchange_regulatory": MockResponseTemplate(
                intent="exchange_regulatory",
                pattern="pre-submission|regulator|regulatory pack|compliance|submission",
                template="""
## Exchange Regulatory Pre-Submission Pack

**Submission Type:** {submission_type}
**Asset Pair:** {asset_pair}
**Analysis Period:** {period}
**Regulatory Authority:** {regulatory_authority}

### Executive Summary:
{execulatory_summary}

### Technical Analysis:
- **Coordination Detection:** {coordination_detection}
- **Risk Assessment:** {risk_assessment}
- **Methodology:** {methodology}
- **Data Sources:** {data_sources}

### Evidence Package:
- **Primary Evidence:** {primary_evidence}
- **Supporting Evidence:** {supporting_evidence}
- **Alternative Explanations:** {alternative_explanations}
- **Provenance Documentation:** {provenance_documentation}

### Compliance Statement:
- **Regulatory Compliance:** {regulatory_compliance}
- **Methodology Validation:** {methodology_validation}
- **Data Integrity:** {data_integrity}
- **Audit Trail:** {audit_trail}

### Recommendations:
- **Immediate Actions:** {immediate_actions}
- **Regulatory Response:** {regulatory_response}
- **Follow-up Actions:** {follow_up_actions}
- **Monitoring Requirements:** {monitoring_requirements}

### Appendices:
- **Technical Appendix:** {technical_appendix}
- **Data Appendix:** {data_appendix}
- **Methodology Appendix:** {methodology_appendix}
- **Provenance Appendix:** {provenance_appendix}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["validation"],
            ),
            "bundle_generation": MockResponseTemplate(
                intent="bundle_generation",
                pattern="bundle|regulatory|compliance memo|draft|generate.*bundle|regulator.*ready",
                template="""
## Regulatory Bundle Generated

**Query:** {prompt}
**Bundle ID:** {bundle_id}
**Generated:** {timestamp}

### Bundle Contents:
- **Executive Summary:** {executive_summary_length} characters
- **Risk Assessment:** {risk_band} risk level
- **Key Findings:** {n_findings} findings identified
- **Recommendations:** {n_recommendations} recommendations provided
- **Attribution Tables:** Risk decomposition available
- **Alternative Explanations:** {n_alternatives} explanations considered

### Bundle Files:
- **JSON Bundle:** {json_path}
- **Attribution Table:** {attribution_path}
- **Provenance:** {provenance_path}

### Refinement Options:
- Add alternative explanations
- Enhance attribution tables
- Include MEV analysis
- Compress or expand content
- Add regulatory language

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["integrated", "report", "attribution"],
            ),
            "bundle_refinement": MockResponseTemplate(
                intent="bundle_refinement",
                pattern="refine|enhance|improve|add.*to.*bundle|modify.*bundle",
                template="""
## Bundle Refinement Applied

**Original Bundle:** {original_bundle_id}
**Refined Bundle:** {refined_bundle_id}
**Refinement Instructions:** {refinement_instructions}

### Refinements Applied:
{refinement_summary}

### Updated Bundle Contents:
- **Executive Summary:** Enhanced with additional detail
- **Key Findings:** {n_findings} findings (refined)
- **Recommendations:** {n_recommendations} recommendations (updated)
- **Alternative Explanations:** {n_alternatives} explanations (expanded)
- **Attribution Tables:** Enhanced with detailed breakdowns

### New Bundle Files:
- **JSON Bundle:** {json_path}
- **Attribution Table:** {attribution_path}
- **Provenance:** {provenance_path}

### Refinement History:
{refinement_history}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["integrated", "report", "attribution"],
            ),
            "bundle_comparison": MockResponseTemplate(
                intent="bundle_comparison",
                pattern="compare.*bundle|difference.*bundle|side.*by.*side|attribution.*comparison",
                template="""
## Bundle Comparison Analysis

**Query:** {prompt}

### Comparison Summary:
- **Bundle 1:** {bundle1_id} - {bundle1_risk_band} risk
- **Bundle 2:** {bundle2_id} - {bundle2_risk_band} risk

### Risk Level Comparison:
| Metric | Bundle 1 | Bundle 2 | Difference |
|--------|----------|----------|------------|
| **Total Risk Score** | {bundle1_score:.1f}/100 | {bundle2_score:.1f}/100 | {score_diff:+.1f} |
| **ICP Contribution** | {bundle1_icp:.1f}/100 | {bundle2_icp:.1f}/100 | {icp_diff:+.1f} |
| **VMM Contribution** | {bundle1_vmm:.1f}/100 | {bundle2_vmm:.1f}/100 | {vmm_diff:+.1f} |
| **Confidence Level** | {bundle1_conf:.1%} | {bundle2_conf:.1%} | {conf_diff:+.1%} |

### Key Differences:
{differences_summary}

### Attribution Comparison:
{attribution_comparison}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["integrated", "report", "attribution"],
            ),
            "bundle_provenance": MockResponseTemplate(
                intent="bundle_provenance",
                pattern="provenance|metadata|audit.*trail|content.*hash|signature",
                template="""
## Bundle Provenance Information

**Bundle ID:** {bundle_id}
**Query:** {prompt}

### Provenance Details:
- **Analysis ID:** {analysis_id}
- **Version:** {version}
- **Content Hash:** {content_hash}
- **Signature:** {signature}
- **Generated:** {generation_timestamp}

### Data Sources:
- **Data Files:** {n_data_files} files
- **Config Files:** {n_config_files} files
- **Result Files:** {n_result_files} files

### Audit Trail:
{audit_trail_summary}

### Configuration:
- **ICP Config:** {icp_config_summary}
- **VMM Config:** {vmm_config_summary}
- **Validation Configs:** {validation_config_summary}

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["integrated", "report", "provenance"],
            ),
            "default": MockResponseTemplate(
                intent="default",
                pattern=".*",
                template="""
## ACD Analysis Response

**Query:** {prompt}

I understand you're asking about algorithmic coordination detection. Based on the available analysis artifacts, here's what I can tell you:

### Available Analysis:
- **ICP Invariance Tests:** Available
- **VMM Moment Analysis:** Available  
- **Validation Layers:** Lead-lag, Mirroring, HMM, Information Flow
- **Risk Assessment:** Integrated scoring available
- **Bundle Generation:** Regulatory-ready bundles available

### Next Steps:
Please be more specific about which aspect of the analysis you'd like to explore:
- Mirroring ratios and coordination patterns
- Lead-lag relationships and persistence
- Spread floor detection and regime analysis
- Overall risk assessment and recommendations
- Generate regulatory bundles
- Refine existing bundles

### Data Sources:
- Analysis artifacts: {artifact_paths}
- Seed: {seed}
- Timestamp: {timestamp}
""",
                requires_artifacts=["validation"],
            ),
        }

    def _load_fixtures(self) -> Dict[str, Any]:
        """Load fixture data for mock responses"""
        return {
            "default_period": "Last 7 days",
            "default_asset": "BTC/USD",
            "default_seed": "42",
            "default_timestamp": self._get_timestamp(),
            "interpretations": {
                "mirroring_high": "High mirroring ratios suggest potential coordination between exchanges.",
                "mirroring_low": "Low mirroring ratios indicate competitive pricing behavior.",
                "lead_lag_persistent": "Low switching entropy suggests persistent leadership patterns.",
                "lead_lag_competitive": "High switching entropy indicates competitive leadership dynamics.",
                "spread_floor_detected": "Spread floor patterns detected, suggesting potential coordination.",
                "spread_floor_none": "No significant spread floor patterns detected.",
                "icp_reject": "ICP rejects invariance, suggesting coordination across environments.",
                "icp_accept": "ICP accepts invariance, suggesting competitive behavior.",
                "vmm_reject": "VMM rejects moment conditions, indicating structural instability.",
                "vmm_accept": "VMM accepts moment conditions, indicating structural stability.",
            },
        }

    def _detect_intent(self, prompt: str) -> str:
        """Detect user intent from prompt text"""
        prompt_lower = prompt.lower()

        # Check exchange-specific intents first (more specific patterns first)
        exchange_intents = [
            "exchange_market_maker",
            "exchange_surveillance",
            "exchange_lead_lag",
            "exchange_mirroring",
            "exchange_fee_analysis",
            "exchange_case_management",
            "exchange_comparison",
            "exchange_simulation",
            "exchange_risk_summary",
            "exchange_reporting",
            "exchange_visualization",
            "exchange_regulatory",
        ]

        # Check exchange-specific templates first with more specific matching
        for intent in exchange_intents:
            if intent in self.templates:
                template = self.templates[intent]
                patterns = template.pattern.split("|")

                # For some intents, require multiple pattern matches
                if intent == "exchange_mirroring":
                    # Require both "mirroring" and one of the specific terms
                    if "mirroring" in prompt_lower and any(
                        word in prompt_lower for word in ["episodes", "heatmap", "depth tier"]
                    ):
                        return intent
                elif intent == "exchange_market_maker":
                    # Require both "market maker" and one of the specific terms
                    if "market maker" in prompt_lower and any(
                        word in prompt_lower for word in ["undercut", "escalate", "episodes"]
                    ):
                        return intent
                elif intent == "exchange_lead_lag":
                    # Require specific lead-lag terms
                    if any(
                        word in prompt_lower
                        for word in [
                            "who led",
                            "btc/usdt",
                            "coinbase",
                            "binance",
                            "switching entropy",
                        ]
                    ):
                        return intent
                else:
                    # Default pattern matching for other intents
                    if any(word in prompt_lower for word in patterns):
                        return intent

        # Then check other specific intents
        for intent, template in self.templates.items():
            if intent == "default" or intent in exchange_intents:
                continue

            # Simple pattern matching (in real implementation, use NLP)
            if any(word in prompt_lower for word in template.pattern.split("|")):
                return intent

        return "default"

    def _load_relevant_artifacts(self, required_artifacts: List[str]) -> Dict[str, Any]:
        """Load relevant artifacts for response generation"""
        artifacts = {}

        for artifact_type in required_artifacts:
            try:
                if artifact_type == "validation":
                    # Load validation artifacts
                    validation_files = list(self.artifacts_dir.glob("**/validation_*.json"))
                    if validation_files:
                        with open(validation_files[0], "r") as f:
                            artifacts[artifact_type] = json.load(f)

                elif artifact_type == "icp":
                    # Load ICP artifacts
                    icp_files = list(self.artifacts_dir.glob("**/icp_*.json"))
                    if icp_files:
                        with open(icp_files[0], "r") as f:
                            artifacts[artifact_type] = json.load(f)

                elif artifact_type == "vmm":
                    # Load VMM artifacts
                    vmm_files = list(self.artifacts_dir.glob("**/vmm_*.json"))
                    if vmm_files:
                        with open(vmm_files[0], "r") as f:
                            artifacts[artifact_type] = json.load(f)

                elif artifact_type == "integrated":
                    # Load integrated analysis artifacts
                    integrated_files = list(self.artifacts_dir.glob("**/integrated_*.json"))
                    if integrated_files:
                        with open(integrated_files[0], "r") as f:
                            artifacts[artifact_type] = json.load(f)

                elif artifact_type == "report":
                    # Load report artifacts
                    report_files = list(self.artifacts_dir.glob("**/report_*.json"))
                    if report_files:
                        with open(report_files[0], "r") as f:
                            artifacts[artifact_type] = json.load(f)

            except Exception as e:
                logger.warning(f"Could not load {artifact_type} artifacts: {e}")
                # Use default values
                artifacts[artifact_type] = self._get_default_artifact_data(artifact_type)

        return artifacts

    def _get_default_artifact_data(self, artifact_type: str) -> Dict[str, Any]:
        """Get default artifact data when real artifacts are unavailable"""
        defaults = {
            "validation": {
                "mirroring": {"coordination_score": 0.5, "mirroring_ratio": 0.7},
                "lead_lag": {"switching_entropy": 0.8, "significant_relationships": 3},
                "hmm": {"regime_stability": 0.6, "coordination_regime_score": 0.4},
            },
            "icp": {"invariance_p_value": 0.05, "power": 0.8, "n_environments": 2},
            "vmm": {"over_identification_p_value": 0.05, "structural_stability": 0.7},
            "integrated": {"composite_score": 50.0, "risk_band": "AMBER"},
            "report": {"summary": {"overall_risk_assessment": "AMBER"}},
        }
        return defaults.get(artifact_type, {})

    def _render_template(
        self, template: MockResponseTemplate, prompt: str, artifacts: Dict[str, Any]
    ) -> str:
        """Render template with artifact data"""
        # Extract data from artifacts
        data = {
            "prompt": prompt,
            "period": self.fixtures["default_period"],
            "asset_pair": self.fixtures["default_asset"],
            "seed": self.fixtures["default_seed"],
            "timestamp": self.fixtures["default_timestamp"],
            "artifact_paths": ", ".join(artifacts.keys()),
        }

        # Add specific data based on template type
        if template.intent == "mirroring_analysis":
            validation = artifacts.get("validation", {})
            mirroring = validation.get("mirroring", {})
            data.update(
                {
                    "mirroring_ratio": mirroring.get("mirroring_ratio", 0.7),
                    "coordination_score": mirroring.get("coordination_score", 0.5),
                    "high_mirroring_pairs": mirroring.get("high_mirroring_pairs", 2),
                    "mirroring_interpretation": self.fixtures["interpretations"]["mirroring_high"],
                }
            )

        elif template.intent == "lead_lag_analysis":
            validation = artifacts.get("validation", {})
            lead_lag = validation.get("lead_lag", {})
            data.update(
                {
                    "switching_entropy": lead_lag.get("switching_entropy", 0.8),
                    "significant_relationships": lead_lag.get("significant_relationships", 3),
                    "persistence_scores": lead_lag.get("persistence_scores", [0.6, 0.7, 0.5]),
                    "lead_lag_interpretation": self.fixtures["interpretations"][
                        "lead_lag_competitive"
                    ],
                }
            )

        elif template.intent == "spread_floor_analysis":
            validation = artifacts.get("validation", {})
            hmm = validation.get("hmm", {})
            data.update(
                {
                    "regime_stability": hmm.get("regime_stability", 0.6),
                    "coordination_regime_score": hmm.get("coordination_regime_score", 0.4),
                    "wide_spread_regime": hmm.get("wide_spread_regime", "State 2"),
                    "lockstep_regime": hmm.get("lockstep_regime", "State 1"),
                    "spread_floor_interpretation": self.fixtures["interpretations"][
                        "spread_floor_none"
                    ],
                }
            )

        elif template.intent == "icp_analysis":
            icp = artifacts.get("icp", {})
            data.update(
                {
                    "icp_p_value": icp.get("invariance_p_value", 0.05),
                    "power": icp.get("power", 0.8),
                    "n_environments": icp.get("n_environments", 2),
                    "environment_sizes": icp.get("environment_sizes", [100, 100]),
                    "icp_interpretation": self.fixtures["interpretations"]["icp_accept"],
                }
            )

        elif template.intent == "vmm_analysis":
            vmm = artifacts.get("vmm", {})
            data.update(
                {
                    "vmm_p_value": vmm.get("over_identification_p_value", 0.05),
                    "structural_stability": vmm.get("structural_stability", 0.7),
                    "n_moments": vmm.get("n_moments", 17),
                    "convergence_achieved": vmm.get("convergence_achieved", True),
                    "vmm_interpretation": self.fixtures["interpretations"]["vmm_accept"],
                }
            )

        # Exchange-specific template rendering
        elif template.intent == "exchange_surveillance":
            data.update(
                {
                    "venue": "Our Exchange",
                    "spread_floor_persistence": 85.2,
                    "volatility_during_persistence": 4.5,
                    "suspicious_periods": "3 periods identified",
                    "risk_level": "AMBER",
                    "order_book_evidence": "order_book_data_2025-09-20.json",
                    "trade_evidence": "trade_data_2025-09-20.json",
                    "coordination_evidence": "coordination_signals.json",
                    "provenance_hash": "sha256:abc123...",
                    "immediate_actions": "Investigate spread floor persistence patterns",
                    "investigation_priority": "HIGH",
                    "regulatory_risk": "MODERATE",
                }
            )

        elif template.intent == "exchange_lead_lag":
            data.update(
                {
                    "time_window": "10:00-14:00 UTC",
                    "our_venue_leadership": 65.0,
                    "coinbase_leadership": 25.0,
                    "binance_leadership": 10.0,
                    "persistence_score": 0.78,
                    "switching_entropy": 0.23,
                    "dominant_leader": "Our Venue",
                    "leadership_stability": "HIGH",
                    "suspicious_patterns": "Low switching entropy detected",
                    "risk_level": "AMBER",
                    "coordination_indicators": "Persistent leadership with low switching",
                    "investigation_required": "YES",
                }
            )

        elif template.intent == "exchange_mirroring":
            data.update(
                {
                    "high_mirroring_episodes": "5 episodes identified",
                    "avg_mirroring_ratio": 0.82,
                    "peak_mirroring_ratio": 0.95,
                    "external_venue_correlation": 0.78,
                    "arbitrage_opportunities": "Limited due to high mirroring",
                    "window_duration": "2-5 minutes",
                    "profit_potential": "Low",
                    "top3_depth_mirroring": 0.88,
                    "mid_depth_mirroring": 0.75,
                    "deep_book_mirroring": 0.65,
                    "risk_level": "AMBER",
                    "coordination_indicators": "High mirroring ratios across depth tiers",
                    "market_impact": "Reduced arbitrage opportunities",
                }
            )

        elif template.intent == "exchange_fee_analysis":
            data.update(
                {
                    "signal_date": "2025-09-15",
                    "fee_tier_structure": "VIP, Premium, Standard",
                    "vip_benefits": "Reduced maker fees, priority support",
                    "volume_thresholds": "VIP: $10M+, Premium: $1M+",
                    "fee_impact_on_signal": "MODERATE - VIP tier may incentivize coordination",
                    "inventory_changes": "15% inventory reduction detected",
                    "shock_magnitude": 15.0,
                    "recovery_time": "2 hours",
                    "inventory_impact_on_signal": "HIGH - inventory shock explains 60% of signal",
                    "primary_driver": "Inventory shock",
                    "secondary_factors": "VIP fee tier incentives",
                    "alternative_explanations": "Market volatility, regulatory events",
                    "confidence_level": 85.0,
                    "risk_level": "LOW",
                    "regulatory_implications": "MINIMAL",
                    "recommended_actions": "Monitor inventory levels, review fee tier structure",
                }
            )

        elif template.intent == "exchange_case_management":
            data.update(
                {
                    "alert_id": "23198",
                    "case_status": "OPEN",
                    "analysis_date": "2025-09-21",
                    "icp_p_value": 0.013,
                    "icp_power": 0.85,
                    "vmm_p_value": 0.045,
                    "vmm_stability": 0.72,
                    "coordination_detected": "YES",
                    "data_hash": "sha256:def456...",
                    "analysis_hash": "sha256:ghi789...",
                    "case_file_hash": "sha256:jkl012...",
                    "audit_trail": "Complete audit trail available",
                    "executive_summary": "Coordination signals detected in BTC/USD pair",
                    "technical_analysis": "ICP and VMM analysis confirm coordination",
                    "evidence_files": "order_book_data.json, trade_data.json",
                    "recommendations": "Investigate further, prepare regulatory submission",
                    "priority_level": "HIGH",
                    "assigned_to": "Surveillance Team",
                    "due_date": "2025-09-28",
                    "investigation_status": "IN PROGRESS",
                }
            )

        elif template.intent == "exchange_comparison":
            data.update(
                {
                    "analysis_period": "Today",
                    "baseline_period": "Last week",
                    "current_risk_level": "AMBER",
                    "baseline_risk_level": "GREEN",
                    "risk_change": "INCREASED",
                    "lead_lag_change": 0.15,
                    "mirroring_change": 0.08,
                    "spread_floor_change": 0.12,
                    "undercut_change": "+3 episodes",
                    "lead_lag_validation_change": "More persistent patterns",
                    "mirroring_validation_change": "Higher ratios detected",
                    "hmm_regime_change": "State transition observed",
                    "infoflow_change": "Increased information flow",
                    "primary_changes": "Increased coordination signals",
                    "secondary_changes": "Market volatility increase",
                    "market_conditions": "Higher volatility, increased trading volume",
                    "external_factors": "Regulatory announcements, market events",
                    "overall_risk_change": "SIGNIFICANT INCREASE",
                    "investigation_required": "YES",
                    "recommended_actions": "Immediate investigation, enhanced monitoring",
                }
            )

        elif template.intent == "exchange_simulation":
            data.update(
                {
                    "simulation_type": "Latency-Arb Constraint Simulation",
                    "latency_arb_constraints": "Stricter thresholds applied",
                    "stricter_thresholds": "50% reduction in tolerance",
                    "simulation_duration": "24 hours",
                    "red_flag_persistence": "PERSISTS",
                    "risk_level_change": "RED to AMBER",
                    "coordination_signals": "Reduced but still present",
                    "false_positive_rate": 15.0,
                    "market_impact": "MODERATE",
                    "volume_impact": 5.0,
                    "spread_impact": 0.002,
                    "liquidity_impact": "MINIMAL",
                    "constraint_effectiveness": "PARTIAL",
                    "implementation_feasibility": "HIGH",
                    "risk_benefit_analysis": "BENEFICIAL",
                    "next_steps": "Implement constraints, monitor results",
                }
            )

        elif template.intent == "exchange_risk_summary":
            data.update(
                {
                    "assessment_date": "2025-09-21",
                    "btc_risk_level": "AMBER",
                    "eth_risk_level": "GREEN",
                    "overall_risk_level": "AMBER",
                    "risk_trend": "INCREASING",
                    "surveillance_actions": "Enhanced monitoring implemented",
                    "investigation_actions": "3 cases opened",
                    "compliance_actions": "Regulatory reporting prepared",
                    "market_actions": "Market maker warnings issued",
                    "high_priority_tickets": 2,
                    "medium_priority_tickets": 5,
                    "low_priority_tickets": 8,
                    "total_open_tickets": 15,
                    "coordination_signals": "5 signals detected",
                    "false_positive_rate": 20.0,
                    "investigation_success_rate": 75.0,
                    "avg_resolution_time": "3.2 days",
                    "immediate_actions": "Investigate high-priority tickets",
                    "medium_term_actions": "Review surveillance thresholds",
                    "long_term_actions": "Enhance coordination detection",
                    "resource_requirements": "Additional surveillance staff needed",
                }
            )

        elif template.intent == "exchange_reporting":
            data.update(
                {
                    "recipient": "CCO",
                    "sender": "Surveillance Team",
                    "memo_date": "2025-09-21",
                    "subject": "Coordination Signals Analysis - BTC/USD",
                    "executive_summary": "Coordination signals detected in BTC/USD pair requiring immediate attention",
                    "coordination_signals": "5 signals detected with 85% confidence",
                    "risk_assessment": "AMBER risk level with increasing trend",
                    "market_impact": "Reduced arbitrage opportunities, potential market manipulation",
                    "regulatory_implications": "Potential regulatory scrutiny if patterns persist",
                    "data_limitations": "Limited historical data for comparison",
                    "analysis_constraints": "Real-time analysis only, no historical validation",
                    "uncertainty_factors": "Market volatility, external events",
                    "assumptions_made": "Standard market conditions, no technical issues",
                    "arbitrage_latency_explanation": "Cross-venue latency may explain some patterns",
                    "fee_tier_explanation": "VIP fee tiers may incentivize coordination",
                    "inventory_shock_explanation": "Market maker inventory changes may drive signals",
                    "market_conditions_explanation": "High volatility may trigger similar responses",
                    "immediate_actions": "Investigate coordination signals, prepare case files",
                    "short_term_actions": "Enhanced monitoring, market maker warnings",
                    "medium_term_actions": "Review fee tier structure, improve surveillance",
                    "long_term_actions": "Develop advanced coordination detection",
                    "personnel_requirements": "Additional surveillance analyst",
                    "technology_requirements": "Enhanced monitoring tools",
                    "budget_requirements": "$50K for additional resources",
                    "timeline_requirements": "Immediate for high-priority items",
                }
            )

        elif template.intent == "exchange_visualization":
            data.update(
                {
                    "visualization_type": "Order-Book Mirroring Heatmap",
                    "trading_hours": "US Trading Hours (14:00-21:00 UTC)",
                    "depth_tier_1_3_mirroring": 0.88,
                    "depth_tier_4_6_mirroring": 0.75,
                    "depth_tier_7_10_mirroring": 0.65,
                    "overall_mirroring": 0.76,
                    "us_trading_hours_mirroring": 0.82,
                    "european_hours_mirroring": 0.68,
                    "asian_hours_mirroring": 0.71,
                    "peak_mirroring_time": "15:30 UTC",
                    "high_mirroring_periods": "US market open, European close",
                    "low_mirroring_periods": "Asian hours, market transitions",
                    "pattern_analysis": "Systematic mirroring during high-volume periods",
                    "anomaly_detection": "2 anomalous periods identified",
                    "risk_level": "AMBER",
                    "coordination_indicators": "High mirroring during peak trading hours",
                    "investigation_priority": "MEDIUM",
                }
            )

        elif template.intent == "exchange_market_maker":
            data.update(
                {
                    "market_maker_focus": "All market makers",
                    "total_episodes": 12,
                    "episodes_by_mm": "MM1: 5, MM2: 4, MM3: 3",
                    "avg_undercut_size": 0.002,
                    "peak_undercut_size": 0.005,
                    "most_active_mm": "MM1",
                    "highest_undercut_rate": "MM1: 0.8%",
                    "suspicious_patterns": "Systematic undercutting by MM1",
                    "repeat_offenders": "MM1, MM2",
                    "escalation_required": "YES",
                    "escalation_reasons": "Repeated undercutting patterns",
                    "priority_level": "HIGH",
                    "recommended_actions": "Investigate MM1, review market maker agreements",
                    "risk_level": "AMBER",
                    "coordination_indicators": "Systematic undercutting patterns",
                    "market_impact": "Reduced market efficiency",
                    "regulatory_risk": "MODERATE",
                    "cases_opened": 2,
                    "cases_closed": 1,
                    "open_investigations": 1,
                    "resolution_rate": 50.0,
                }
            )

        elif template.intent == "exchange_regulatory":
            data.update(
                {
                    "submission_type": "Pre-Submission Pack",
                    "regulatory_authority": "SEC Division of Trading and Markets",
                    "execulatory_summary": "Coordination signals detected in cryptocurrency trading",
                    "coordination_detection": "ICP and VMM analysis confirm coordination",
                    "risk_assessment": "AMBER risk level with regulatory implications",
                    "methodology": "Invariant Causal Prediction and Variational Method of Moments",
                    "data_sources": "Order book data, trade data, venue status",
                    "primary_evidence": "Coordination signals, persistence analysis",
                    "supporting_evidence": "Market data, venue comparisons",
                    "alternative_explanations": "Arbitrage latency, fee tier incentives",
                    "provenance_documentation": "Complete audit trail and metadata",
                    "regulatory_compliance": "Full compliance with surveillance requirements",
                    "methodology_validation": "Peer-reviewed methodology",
                    "data_integrity": "Cryptographic verification",
                    "audit_trail": "Complete audit trail available",
                    "immediate_actions": "Enhanced monitoring, investigation",
                    "regulatory_response": "Proactive reporting to regulators",
                    "follow_up_actions": "Regular reporting, methodology updates",
                    "monitoring_requirements": "Continuous monitoring, quarterly reports",
                    "technical_appendix": "Detailed methodology and analysis",
                    "data_appendix": "Raw data and processing steps",
                    "methodology_appendix": "Statistical methods and validation",
                    "provenance_appendix": "Audit trail and verification",
                }
            )

        elif template.intent == "risk_assessment":
            integrated = artifacts.get("integrated", {})
            data.update(
                {
                    "risk_level": integrated.get("risk_band", "AMBER"),
                    "coordination_detected": integrated.get("composite_score", 50) > 60,
                    "confidence_level": "Medium",
                    "composite_score": integrated.get("composite_score", 50),
                    "icp_contribution": integrated.get("icp_contribution", 0.4),
                    "vmm_contribution": integrated.get("vmm_contribution", 0.4),
                }
            )

        elif template.intent == "alternative_explanations":
            data.update(
                {
                    "arbitrage_analysis": "Latency constraints were within normal ranges",
                    "fee_analysis": "Fee tier structures showed no significant impact",
                    "inventory_analysis": "Inventory shocks were not detected during the analysis period",
                    "volatility_analysis": "Volatility controls were properly applied",
                    "explanation_conclusion": "Alternative explanations do not fully account for the observed coordination patterns",
                }
            )

        elif template.intent == "bundle_generation":
            integrated = artifacts.get("integrated", {})
            attribution = artifacts.get("attribution", {})
            data.update(
                {
                    "bundle_id": f"ACD_BUNDLE_{self.fixtures['default_seed']}_{self.fixtures['default_timestamp'].replace(':', '').replace('-', '').replace(' ', '_')}",
                    "executive_summary_length": 528,
                    "risk_band": integrated.get("risk_band", "AMBER"),
                    "n_findings": 3,
                    "n_recommendations": 6,
                    "n_alternatives": 3,
                    "json_path": f"artifacts/reports/bundle_{self.fixtures['default_seed']}.json",
                    "attribution_path": f"artifacts/reports/attribution_{self.fixtures['default_seed']}.json",
                    "provenance_path": f"artifacts/reports/provenance_{self.fixtures['default_seed']}.json",
                }
            )

        elif template.intent == "bundle_refinement":
            integrated = artifacts.get("integrated", {})
            data.update(
                {
                    "original_bundle_id": f"ACD_BUNDLE_{self.fixtures['default_seed']}_original",
                    "refined_bundle_id": f"ACD_BUNDLE_{self.fixtures['default_seed']}_refined_1",
                    "refinement_instructions": "Enhance alternative explanations, Add attribution tables",
                    "refinement_summary": "Applied 2 refinement instructions: enhanced alternative explanations and added detailed attribution tables",
                    "n_findings": 4,
                    "n_recommendations": 7,
                    "n_alternatives": 5,
                    "json_path": f"artifacts/reports/refined_bundle_{self.fixtures['default_seed']}.json",
                    "attribution_path": f"artifacts/reports/refined_attribution_{self.fixtures['default_seed']}.json",
                    "provenance_path": f"artifacts/reports/refined_provenance_{self.fixtures['default_seed']}.json",
                    "refinement_history": f"1. Enhanced alternative explanations at {self.fixtures['default_timestamp']}\n2. Added attribution tables at {self.fixtures['default_timestamp']}",
                }
            )

        elif template.intent == "bundle_comparison":
            data.update(
                {
                    "bundle1_id": f"ACD_BUNDLE_{self.fixtures['default_seed']}_1",
                    "bundle2_id": f"ACD_BUNDLE_{self.fixtures['default_seed'] + 1}_2",
                    "bundle1_risk_band": "AMBER",
                    "bundle2_risk_band": "LOW",
                    "bundle1_score": 75.5,
                    "bundle2_score": 45.2,
                    "score_diff": 30.3,
                    "bundle1_icp": 68.5,
                    "bundle2_icp": 25.0,
                    "icp_diff": 43.5,
                    "bundle1_vmm": 57.5,
                    "bundle2_vmm": 35.0,
                    "vmm_diff": 22.5,
                    "bundle1_conf": 0.85,
                    "bundle2_conf": 0.70,
                    "conf_diff": 0.15,
                    "differences_summary": "Bundle 1 shows significantly higher coordination risk with stronger ICP and VMM signals",
                    "attribution_comparison": "Bundle 1 has higher attribution across all components, particularly ICP analysis",
                }
            )

        elif template.intent == "bundle_provenance":
            data.update(
                {
                    "bundle_id": f"ACD_BUNDLE_{self.fixtures['default_seed']}",
                    "analysis_id": f"ACD_ANALYSIS_{self.fixtures['default_seed']}",
                    "version": "2.0.0",
                    "content_hash": f"abc123def456{self.fixtures['default_seed']}",
                    "signature": f"ACD_SIG_abc123def456{self.fixtures['default_seed']}",
                    "generation_timestamp": self.fixtures["default_timestamp"],
                    "n_data_files": 2,
                    "n_config_files": 1,
                    "n_result_files": 4,
                    "audit_trail_summary": f"1. Analysis initiated at {self.fixtures['default_timestamp']}\n2. Bundle generated at {self.fixtures['default_timestamp']}\n3. Provenance tracked with hash verification",
                    "icp_config_summary": "significance_level: 0.05, n_bootstrap: 1000",
                    "vmm_config_summary": "max_iterations: 1000, convergence_tolerance: 1e-6",
                    "validation_config_summary": "lead_lag: window_size=30, mirroring: threshold=0.7",
                }
            )

        # Render template
        try:
            return template.template.format(**data)
        except KeyError as e:
            logger.error(f"Template rendering error: {e}")
            return f"Error rendering template: {e}"

    def _find_recent_artifacts(self) -> List[Path]:
        """Find recent artifact files"""
        if not self.artifacts_dir.exists():
            return []

        # Find JSON files modified in last 24 hours
        import time

        cutoff_time = time.time() - 24 * 3600

        recent_files = []
        for json_file in self.artifacts_dir.glob("**/*.json"):
            if json_file.stat().st_mtime > cutoff_time:
                recent_files.append(json_file)

        return recent_files

    def _get_error_response(
        self, prompt: str, session_id: Optional[str], error: str
    ) -> AgentMessage:
        """Generate error response"""
        return AgentMessage(
            content=f"[Error] I encountered an issue processing your request: {error}. Please try again or contact support.",
            session_id=session_id or f"error_{hash(prompt) % 10000}",
            usage={"mode": "error", "error": error},
            metadata={"provider": "offline_mock", "error": error},
        )

    def _get_timestamp(self) -> str:
        """Get current timestamp as ISO string"""
        from datetime import datetime

        return datetime.now().isoformat()
