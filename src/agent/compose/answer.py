"""
ACD Answer Composer

This module provides functionality to compose structured answers from
ACD artifacts and analysis results for agent responses.
"""

import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ComposedAnswer:
    """Structured answer with metrics and provenance"""

    content: str
    metrics: Dict[str, Any]
    provenance: Dict[str, Any]
    confidence: float
    answer_type: str


class ACDAnswerComposer:
    """
    Composes structured answers from ACD artifacts

    This class takes selected artifacts and composes human-readable
    answers with embedded metrics and provenance information.
    """

    def __init__(self):
        self.templates = self._load_answer_templates()
        self.metric_formatters = self._load_metric_formatters()

        logger.info("ACDAnswerComposer initialized")

    def compose_answer(
        self, query: str, selected_artifacts: Dict[str, Any], intent: Any
    ) -> ComposedAnswer:
        """
        Compose answer from selected artifacts

        Args:
            query: Original user query
            selected_artifacts: Artifacts selected by selector
            intent: Query intent information

        Returns:
            ComposedAnswer with structured content
        """
        try:
            # Determine answer type based on intent
            answer_type = self._determine_answer_type(intent, selected_artifacts)

            # Extract metrics from artifacts
            metrics = self._extract_metrics(selected_artifacts)

            # Generate provenance information
            provenance = self._generate_provenance(selected_artifacts)

            # Compose content based on answer type
            content = self._compose_content(query, answer_type, metrics, provenance, intent)

            # Calculate confidence based on data quality
            confidence = self._calculate_confidence(selected_artifacts, metrics)

            return ComposedAnswer(
                content=content,
                metrics=metrics,
                provenance=provenance,
                confidence=confidence,
                answer_type=answer_type,
            )

        except Exception as e:
            logger.error(f"Error composing answer: {e}")
            return self._get_error_answer(query, str(e))

    def _determine_answer_type(self, intent: Any, artifacts: Dict[str, Any]) -> str:
        """Determine the type of answer to compose"""
        if intent.intent_type == "mirroring_analysis":
            return "mirroring_analysis"
        elif intent.intent_type == "lead_lag_analysis":
            return "lead_lag_analysis"
        elif intent.intent_type == "spread_floor_analysis":
            return "spread_floor_analysis"
        elif intent.intent_type == "icp_analysis":
            return "icp_analysis"
        elif intent.intent_type == "vmm_analysis":
            return "vmm_analysis"
        elif intent.intent_type == "risk_assessment":
            return "risk_assessment"
        elif intent.intent_type == "atp_case":
            return "atp_case"
        elif intent.intent_type == "artifacts_list":
            return "artifacts_list"
        else:
            return "general_analysis"

    def _extract_metrics(self, artifacts: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant metrics from artifacts"""
        metrics = {}

        try:
            for artifact_name, artifact_data in artifacts.items():
                if isinstance(artifact_data, dict):
                    # Extract metrics based on artifact type
                    if "validation" in artifact_name:
                        metrics.update(self._extract_validation_metrics(artifact_data))
                    elif "icp" in artifact_name:
                        metrics.update(self._extract_icp_metrics(artifact_data))
                    elif "vmm" in artifact_name:
                        metrics.update(self._extract_vmm_metrics(artifact_data))
                    elif "integrated" in artifact_name:
                        metrics.update(self._extract_integrated_metrics(artifact_data))
                    elif "atp_case" in artifact_name:
                        metrics.update(self._extract_atp_metrics(artifact_data))

        except Exception as e:
            logger.error(f"Error extracting metrics: {e}")
            metrics["extraction_error"] = str(e)

        return metrics

    def _extract_validation_metrics(self, validation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metrics from validation data"""
        metrics = {}

        # Lead-lag metrics
        if "lead_lag" in validation_data:
            lead_lag = validation_data["lead_lag"]
            metrics.update(
                {
                    "switching_entropy": lead_lag.get("switching_entropy"),
                    "significant_relationships": lead_lag.get("significant_relationships"),
                    "avg_granger_p": lead_lag.get("avg_granger_p"),
                }
            )

        # Mirroring metrics
        if "mirroring" in validation_data:
            mirroring = validation_data["mirroring"]
            metrics.update(
                {
                    "coordination_score": mirroring.get("coordination_score"),
                    "mirroring_ratio": mirroring.get("mirroring_ratio"),
                    "avg_cosine_similarity": mirroring.get("avg_cosine_similarity"),
                }
            )

        # HMM metrics
        if "hmm" in validation_data:
            hmm = validation_data["hmm"]
            metrics.update(
                {
                    "regime_stability": hmm.get("regime_stability"),
                    "coordination_regime_score": hmm.get("coordination_regime_score"),
                    "log_likelihood": hmm.get("log_likelihood"),
                }
            )

        # Information flow metrics
        if "infoflow" in validation_data:
            infoflow = validation_data["infoflow"]
            metrics.update(
                {
                    "coordination_network_score": infoflow.get("coordination_network_score"),
                    "avg_transfer_entropy": infoflow.get("avg_transfer_entropy"),
                    "out_degree_concentration": infoflow.get("out_degree_concentration"),
                }
            )

        return metrics

    def _extract_icp_metrics(self, icp_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metrics from ICP data"""
        return {
            "invariance_p_value": icp_data.get("invariance_p_value"),
            "power": icp_data.get("power"),
            "n_environments": icp_data.get("n_environments"),
            "environment_sizes": icp_data.get("environment_sizes"),
        }

    def _extract_vmm_metrics(self, vmm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metrics from VMM data"""
        return {
            "over_identification_p_value": vmm_data.get("over_identification_p_value"),
            "structural_stability": vmm_data.get("structural_stability"),
            "n_moments": vmm_data.get("n_moments"),
            "convergence_achieved": vmm_data.get("convergence_achieved"),
        }

    def _extract_integrated_metrics(self, integrated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metrics from integrated analysis data"""
        return {
            "composite_score": integrated_data.get("composite_score"),
            "risk_band": integrated_data.get("risk_band"),
            "icp_contribution": integrated_data.get("icp_contribution"),
            "vmm_contribution": integrated_data.get("vmm_contribution"),
            "crypto_contribution": integrated_data.get("crypto_contribution"),
        }

    def _extract_atp_metrics(self, atp_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metrics from ATP case data"""
        metrics = {}

        # Extract from report summary
        if "report" in atp_data and "summary" in atp_data["report"]:
            summary = atp_data["report"]["summary"]
            metrics.update(
                {
                    "overall_risk_assessment": summary.get("overall_risk_assessment"),
                    "coordination_detected": summary.get("coordination_detected"),
                    "confidence_level": summary.get("confidence_level"),
                }
            )

        # Extract from individual analyses
        for analysis_type in ["icp", "vmm", "validation"]:
            if analysis_type in atp_data:
                analysis_data = atp_data[analysis_type]
                if analysis_type == "icp":
                    metrics.update(self._extract_icp_metrics(analysis_data))
                elif analysis_type == "vmm":
                    metrics.update(self._extract_vmm_metrics(analysis_data))
                elif analysis_type == "validation":
                    metrics.update(self._extract_validation_metrics(analysis_data))

        return metrics

    def _generate_provenance(self, artifacts: Dict[str, Any]) -> Dict[str, Any]:
        """Generate provenance information from artifacts"""
        provenance = {
            "artifact_count": len(artifacts),
            "artifact_types": list(artifacts.keys()),
            "data_sources": [],
            "analysis_timestamps": [],
            "seeds_used": [],
        }

        try:
            for artifact_name, artifact_data in artifacts.items():
                if isinstance(artifact_data, dict):
                    # Extract timestamp information
                    if "analysis_timestamp" in artifact_data:
                        provenance["analysis_timestamps"].append(
                            artifact_data["analysis_timestamp"]
                        )

                    # Extract seed information
                    if "seed" in artifact_data:
                        provenance["seeds_used"].append(artifact_data["seed"])

                    # Extract file path information
                    if "file_path" in artifact_data:
                        provenance["data_sources"].append(artifact_data["file_path"])

                    # Look for nested provenance
                    if "provenance" in artifact_data:
                        nested_prov = artifact_data["provenance"]
                        if isinstance(nested_prov, dict):
                            provenance["data_sources"].extend(nested_prov.get("data_sources", []))
                            provenance["analysis_timestamps"].extend(
                                nested_prov.get("analysis_timestamps", [])
                            )

        except Exception as e:
            logger.error(f"Error generating provenance: {e}")
            provenance["error"] = str(e)

        return provenance

    def _compose_content(
        self,
        query: str,
        answer_type: str,
        metrics: Dict[str, Any],
        provenance: Dict[str, Any],
        intent: Any,
    ) -> str:
        """Compose the main content of the answer"""
        try:
            # Get template for answer type
            template = self.templates.get(answer_type, self.templates["general"])

            # Format metrics
            formatted_metrics = self._format_metrics(metrics)

            # Build context data
            context = {
                "query": query,
                "answer_type": answer_type,
                "metrics": formatted_metrics,
                "provenance": provenance,
                "intent": intent,
                "artifact_count": provenance.get("artifact_count", 0),
                "data_sources": ", ".join(
                    provenance.get("data_sources", [])[:3]
                ),  # Limit to first 3
            }

            # Render template
            content = template.format(**context)

            return content

        except Exception as e:
            logger.error(f"Error composing content: {e}")
            return f"Error composing answer: {e}"

    def _format_metrics(self, metrics: Dict[str, Any]) -> Dict[str, str]:
        """Format metrics for display"""
        formatted = {}

        for key, value in metrics.items():
            if value is None:
                formatted[key] = "N/A"
            elif isinstance(value, float):
                if "p_value" in key.lower() or "pvalue" in key.lower():
                    formatted[key] = f"{value:.6f}"
                else:
                    formatted[key] = f"{value:.3f}"
            elif isinstance(value, bool):
                formatted[key] = "Yes" if value else "No"
            elif isinstance(value, list):
                formatted[key] = ", ".join(map(str, value[:5]))  # Limit to first 5 items
            else:
                formatted[key] = str(value)

        return formatted

    def _calculate_confidence(self, artifacts: Dict[str, Any], metrics: Dict[str, Any]) -> float:
        """Calculate confidence score based on data quality"""
        confidence = 0.5  # Base confidence

        try:
            # Increase confidence based on artifact count
            artifact_count = len(artifacts)
            if artifact_count > 0:
                confidence += min(0.3, artifact_count * 0.1)

            # Increase confidence based on metric completeness
            metric_count = len([m for m in metrics.values() if m is not None])
            if metric_count > 0:
                confidence += min(0.2, metric_count * 0.05)

            # Decrease confidence if there are errors
            if any("error" in str(v).lower() for v in artifacts.values()):
                confidence -= 0.2

            # Ensure confidence is between 0 and 1
            confidence = max(0.0, min(1.0, confidence))

        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            confidence = 0.3

        return confidence

    def _load_answer_templates(self) -> Dict[str, str]:
        """Load answer templates for different types"""
        return {
            "mirroring_analysis": """
## Mirroring Analysis Results

**Query:** {query}

### Key Metrics:
- **Coordination Score:** {metrics[coordination_score]}
- **Mirroring Ratio:** {metrics[mirroring_ratio]}
- **Average Cosine Similarity:** {metrics[avg_cosine_similarity]}

### Interpretation:
Based on the analysis, the mirroring patterns suggest {interpretation}.

### Data Sources:
Analysis based on {artifact_count} artifacts from: {data_sources}

### Confidence: {confidence:.1%}
""",
            "lead_lag_analysis": """
## Lead-Lag Analysis Results

**Query:** {query}

### Key Metrics:
- **Switching Entropy:** {metrics[switching_entropy]}
- **Significant Relationships:** {metrics[significant_relationships]}
- **Average Granger P-value:** {metrics[avg_granger_p]}

### Interpretation:
The lead-lag analysis indicates {interpretation}.

### Data Sources:
Analysis based on {artifact_count} artifacts from: {data_sources}

### Confidence: {confidence:.1%}
""",
            "risk_assessment": """
## Risk Assessment Summary

**Query:** {query}

### Overall Assessment:
- **Risk Level:** {metrics[overall_risk_assessment]}
- **Coordination Detected:** {metrics[coordination_detected]}
- **Confidence Level:** {metrics[confidence_level]}

### Key Metrics:
- **Composite Score:** {metrics[composite_score]}
- **ICP Contribution:** {metrics[icp_contribution]}
- **VMM Contribution:** {metrics[vmm_contribution]}

### Data Sources:
Analysis based on {artifact_count} artifacts from: {data_sources}

### Confidence: {confidence:.1%}
""",
            "general_analysis": """
## ACD Analysis Response

**Query:** {query}

Based on the available analysis artifacts, here are the key findings:

### Available Metrics:
{formatted_metrics}

### Data Sources:
Analysis based on {artifact_count} artifacts from: {data_sources}

### Confidence: {confidence:.1%}

For more specific analysis, please ask about:
- Mirroring ratios and coordination patterns
- Lead-lag relationships and persistence
- Spread floor detection and regime analysis
- Overall risk assessment and recommendations
""",
        }

    def _load_metric_formatters(self) -> Dict[str, str]:
        """Load metric formatting patterns"""
        return {
            "p_value": "{:.6f}",
            "ratio": "{:.3f}",
            "score": "{:.3f}",
            "entropy": "{:.3f}",
            "stability": "{:.3f}",
            "count": "{:d}",
            "boolean": "{}",
        }

    def _get_error_answer(self, query: str, error: str) -> ComposedAnswer:
        """Get error answer when composition fails"""
        return ComposedAnswer(
            content=f"I encountered an error processing your query: {error}. Please try again or contact support.",
            metrics={"error": error},
            provenance={"error": True},
            confidence=0.0,
            answer_type="error",
        )
