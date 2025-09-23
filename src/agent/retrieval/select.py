"""
ACD Artifact Selector

This module provides intelligent selection of relevant ACD artifacts
based on user queries and context for agent responses.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging

from .loader import ACDArtifactLoader

logger = logging.getLogger(__name__)


@dataclass
class QueryIntent:
    """Detected query intent and context"""

    intent_type: str
    confidence: float
    entities: List[str]
    time_period: Optional[str]
    asset_pair: Optional[str]
    analysis_type: Optional[str]
    specific_metrics: List[str]


class ACDArtifactSelector:
    """
    Selects relevant ACD artifacts based on query analysis

    This class analyzes user queries to determine which artifacts
    are most relevant for generating responses.
    """

    def __init__(self, artifacts_dir: str = "artifacts"):
        self.loader = ACDArtifactLoader(artifacts_dir)
        self.intent_patterns = self._load_intent_patterns()

        logger.info("ACDArtifactSelector initialized")

    def select_artifacts(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Select relevant artifacts based on query analysis

        Args:
            query: User query text
            context: Optional context information

        Returns:
            Dictionary of selected artifacts and metadata
        """
        try:
            # Analyze query intent
            intent = self._analyze_query_intent(query)

            # Select artifacts based on intent
            selected_artifacts = self._select_by_intent(intent, context)

            # Add metadata
            result = {
                "query": query,
                "intent": intent,
                "selected_artifacts": selected_artifacts,
                "selection_metadata": {
                    "total_artifacts": len(selected_artifacts),
                    "intent_confidence": intent.confidence,
                    "selection_reason": self._get_selection_reason(intent),
                },
            }

            logger.info(f"Selected {len(selected_artifacts)} artifacts for query: {query[:50]}...")
            return result

        except Exception as e:
            logger.error(f"Error selecting artifacts for query: {e}")
            return {
                "query": query,
                "error": str(e),
                "selected_artifacts": {},
                "selection_metadata": {"error": True},
            }

    def _analyze_query_intent(self, query: str) -> QueryIntent:
        """
        Analyze query to determine intent and extract entities

        Args:
            query: User query text

        Returns:
            QueryIntent with detected intent and entities
        """
        query_lower = query.lower()

        # Initialize intent
        intent = QueryIntent(
            intent_type="general",
            confidence=0.5,
            entities=[],
            time_period=None,
            asset_pair=None,
            analysis_type=None,
            specific_metrics=[],
        )

        # Detect intent type
        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns["keywords"]:
                if re.search(pattern, query_lower):
                    intent.intent_type = intent_type
                    intent.confidence = min(0.9, intent.confidence + 0.2)
                    break

        # Extract entities
        intent.entities = self._extract_entities(query)

        # Extract time period
        intent.time_period = self._extract_time_period(query)

        # Extract asset pair
        intent.asset_pair = self._extract_asset_pair(query)

        # Extract analysis type
        intent.analysis_type = self._extract_analysis_type(query)

        # Extract specific metrics
        intent.specific_metrics = self._extract_metrics(query)

        return intent

    def _load_intent_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """Load intent detection patterns"""
        return {
            "mirroring_analysis": {
                "keywords": [
                    r"mirroring",
                    r"order book",
                    r"depth",
                    r"cosine",
                    r"similarity",
                    r"coordination.*ratio",
                ],
                "artifacts": ["validation", "mirroring"],
            },
            "lead_lag_analysis": {
                "keywords": [
                    r"lead",
                    r"lag",
                    r"leadership",
                    r"persistence",
                    r"granger",
                    r"causality",
                ],
                "artifacts": ["validation", "lead_lag"],
            },
            "spread_floor_analysis": {
                "keywords": [r"spread floor", r"dwell", r"volatility", r"regime", r"hmm", r"state"],
                "artifacts": ["validation", "hmm"],
            },
            "icp_analysis": {
                "keywords": [r"icp", r"invariance", r"environment", r"fdr", r"bootstrap"],
                "artifacts": ["icp", "validation"],
            },
            "vmm_analysis": {
                "keywords": [r"vmm", r"over.identification", r"stability", r"moments", r"gmm"],
                "artifacts": ["vmm", "validation"],
            },
            "risk_assessment": {
                "keywords": [
                    r"risk",
                    r"summary",
                    r"verdict",
                    r"low",
                    r"amber",
                    r"red",
                    r"assessment",
                ],
                "artifacts": ["integrated", "report"],
            },
            "atp_case": {
                "keywords": [r"atp", r"airline", r"retrospective", r"case study"],
                "artifacts": ["atp_case"],
            },
            "artifacts_list": {
                "keywords": [r"artifacts", r"files", r"data sources", r"provenance", r"seeds"],
                "artifacts": ["all"],
            },
        }

    def _extract_entities(self, query: str) -> List[str]:
        """Extract entities from query"""
        entities = []

        # Common entity patterns
        entity_patterns = [
            r"btc/usd",
            r"eth/usd",
            r"binance",
            r"coinbase",
            r"kraken",
            r"seed\s*(\d+)",
            r"exchange\s*(\w+)",
            r"venue\s*(\w+)",
        ]

        for pattern in entity_patterns:
            matches = re.findall(pattern, query.lower())
            entities.extend(matches)

        return entities

    def _extract_time_period(self, query: str) -> Optional[str]:
        """Extract time period from query"""
        time_patterns = [
            r"last\s+(\d+)\s+days?",
            r"last\s+(\d+)\s+weeks?",
            r"last\s+(\d+)\s+hours?",
            r"yesterday",
            r"today",
            r"past\s+(\d+)\s+days?",
            r"over\s+the\s+last\s+(\d+)\s+days?",
        ]

        for pattern in time_patterns:
            match = re.search(pattern, query.lower())
            if match:
                return match.group(0)

        return None

    def _extract_asset_pair(self, query: str) -> Optional[str]:
        """Extract asset pair from query"""
        asset_patterns = [r"btc/usd", r"eth/usd", r"(\w+)/(\w+)"]

        for pattern in asset_patterns:
            match = re.search(pattern, query.lower())
            if match:
                return match.group(0)

        return None

    def _extract_analysis_type(self, query: str) -> Optional[str]:
        """Extract analysis type from query"""
        analysis_types = [
            "icp",
            "vmm",
            "mirroring",
            "lead_lag",
            "hmm",
            "infoflow",
            "validation",
            "integrated",
            "atp",
            "synthetic",
        ]

        query_lower = query.lower()
        for analysis_type in analysis_types:
            if analysis_type in query_lower:
                return analysis_type

        return None

    def _extract_metrics(self, query: str) -> List[str]:
        """Extract specific metrics from query"""
        metrics = []

        metric_patterns = [
            r"p.value",
            r"p_value",
            r"mirroring ratio",
            r"coordination score",
            r"switching entropy",
            r"regime stability",
            r"structural stability",
            r"over.identification",
            r"granger",
            r"transfer entropy",
        ]

        for pattern in metric_patterns:
            if re.search(pattern, query.lower()):
                metrics.append(pattern)

        return metrics

    def _select_by_intent(
        self, intent: QueryIntent, context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Select artifacts based on detected intent

        Args:
            intent: Detected query intent
            context: Optional context information

        Returns:
            Dictionary of selected artifacts
        """
        selected_artifacts = {}

        try:
            # Get intent patterns
            intent_patterns = self.intent_patterns.get(intent.intent_type, {})
            required_artifacts = intent_patterns.get("artifacts", ["validation"])

            # Select artifacts based on intent
            if "all" in required_artifacts:
                # List all available artifacts
                available_artifacts = self.loader.list_available_artifacts()
                selected_artifacts = available_artifacts

            else:
                # Select specific artifacts
                for artifact_type in required_artifacts:
                    if artifact_type == "validation":
                        # Load validation results for different types
                        validation_types = ["lead_lag", "mirroring", "hmm", "infoflow"]
                        for val_type in validation_types:
                            if intent.analysis_type is None or intent.analysis_type == val_type:
                                result = self.loader.load_validation_results(val_type)
                                if result:
                                    selected_artifacts[f"validation_{val_type}"] = result

                    elif artifact_type == "icp":
                        result = self.loader.load_analysis_report("icp")
                        if result:
                            selected_artifacts["icp"] = result

                    elif artifact_type == "vmm":
                        # Try to load VMM provenance
                        if intent.entities:
                            for entity in intent.entities:
                                if entity.isdigit():
                                    seed = int(entity)
                                    result = self.loader.load_vmm_provenance(seed)
                                    if result:
                                        selected_artifacts[f"vmm_seed_{seed}"] = result
                                        break

                        # Fallback to general VMM results
                        if not selected_artifacts:
                            result = self.loader.load_analysis_report("vmm")
                            if result:
                                selected_artifacts["vmm"] = result

                    elif artifact_type == "integrated":
                        result = self.loader.load_integrated_results()
                        if result:
                            selected_artifacts["integrated"] = result

                    elif artifact_type == "report":
                        result = self.loader.load_analysis_report("integrated")
                        if result:
                            selected_artifacts["report"] = result

                    elif artifact_type == "atp_case":
                        # Try to extract seed from entities
                        seed = 42  # default
                        if intent.entities:
                            for entity in intent.entities:
                                if entity.isdigit():
                                    seed = int(entity)
                                    break

                        result = self.loader.load_atp_case_results(seed)
                        if result:
                            selected_artifacts["atp_case"] = result

            # Add context-specific artifacts if provided
            if context:
                if "seed" in context:
                    vmm_provenance = self.loader.load_vmm_provenance(context["seed"])
                    if vmm_provenance:
                        selected_artifacts[f"vmm_context_seed_{context['seed']}"] = vmm_provenance

        except Exception as e:
            logger.error(f"Error selecting artifacts by intent: {e}")
            selected_artifacts = {"error": str(e)}

        return selected_artifacts

    def _get_selection_reason(self, intent: QueryIntent) -> str:
        """Get human-readable reason for artifact selection"""
        reasons = []

        if intent.intent_type != "general":
            reasons.append(f"Intent: {intent.intent_type}")

        if intent.analysis_type:
            reasons.append(f"Analysis type: {intent.analysis_type}")

        if intent.asset_pair:
            reasons.append(f"Asset pair: {intent.asset_pair}")

        if intent.time_period:
            reasons.append(f"Time period: {intent.time_period}")

        if intent.specific_metrics:
            reasons.append(f"Metrics: {', '.join(intent.specific_metrics)}")

        if not reasons:
            reasons.append("General query - loading default artifacts")

        return "; ".join(reasons)
