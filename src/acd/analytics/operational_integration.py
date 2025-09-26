"""
Operational Integration Module - v1.4 Baseline Standard Implementation

This module implements the operational integration framework required for the v1.4 baseline standard:
- Escalation Matrix (4-tier risk framework: Critical, High, Medium, Low)
- Investigation Protocol (21-day phased investigation steps)
- Decision Matrix (link risk scores to approval authority)

All methods follow the v1.4 professional standards with transparent formulas and economic interpretation.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level enumeration for escalation matrix."""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ApprovalAuthority(Enum):
    """Approval authority enumeration for decision matrix."""

    C_SUITE = "C-Suite"
    CHIEF_RISK_OFFICER = "Chief Risk Officer"
    HEAD_OF_SURVEILLANCE = "Head of Surveillance"
    SENIOR_ANALYST = "Senior Analyst"


@dataclass
class EscalationDecision:
    """Container for escalation decision results."""

    risk_level: RiskLevel
    risk_score: float
    required_actions: List[str]
    timeline: str
    approval_required: ApprovalAuthority
    escalation_notes: str
    decision_date: str


@dataclass
class InvestigationPhase:
    """Container for investigation phase information."""

    phase_number: int
    phase_name: str
    duration_days: int
    objectives: List[str]
    deliverables: List[str]
    success_criteria: List[str]
    responsible_party: str
    escalation_triggers: List[str]


@dataclass
class InvestigationProtocol:
    """Container for complete investigation protocol."""

    total_duration_days: int
    phases: List[InvestigationPhase]
    decision_points: List[str]
    escalation_matrix: Dict[RiskLevel, EscalationDecision]
    success_metrics: Dict[str, float]


class EscalationMatrix:
    """
    Escalation Matrix for 4-Tier Risk Framework

    Implements the v1.4 standard escalation matrix with clear risk levels,
    required actions, timelines, and approval authorities.

    Economic Interpretation: Ensures appropriate escalation of coordination
    risks based on severity and potential market impact.
    """

    def __init__(self):
        """Initialize escalation matrix with v1.4 standards."""
        self.risk_thresholds = {
            RiskLevel.CRITICAL: 8.0,
            RiskLevel.HIGH: 6.0,
            RiskLevel.MEDIUM: 4.0,
            RiskLevel.LOW: 0.0,
        }

        self.escalation_framework = self._initialize_escalation_framework()
        self.logger = logging.getLogger(__name__)

    def _initialize_escalation_framework(self) -> Dict[RiskLevel, Dict]:
        """Initialize escalation framework with v1.4 standards."""
        return {
            RiskLevel.CRITICAL: {
                "risk_score_range": (8.0, 10.0),
                "required_actions": [
                    "Immediate investigation initiation",
                    "Regulatory consultation within 24 hours",
                    "Enhanced monitoring deployment",
                    "Legal review and evidence preservation",
                    "Executive notification to C-Suite",
                ],
                "timeline": "24 hours",
                "approval_required": ApprovalAuthority.C_SUITE,
                "escalation_notes": "Critical coordination risk requiring immediate executive attention and regulatory consultation",
            },
            RiskLevel.HIGH: {
                "risk_score_range": (6.0, 7.9),
                "required_actions": [
                    "Enhanced monitoring activation",
                    "Legal review initiation",
                    "Cross-venue intelligence coordination",
                    "Entity flagging for Level 2 surveillance",
                    "Chief Risk Officer notification",
                ],
                "timeline": "72 hours",
                "approval_required": ApprovalAuthority.CHIEF_RISK_OFFICER,
                "escalation_notes": "High coordination risk requiring enhanced surveillance and legal review",
            },
            RiskLevel.MEDIUM: {
                "risk_score_range": (4.0, 5.9),
                "required_actions": [
                    "Surveillance escalation",
                    "Documentation and evidence collection",
                    "Cross-venue data correlation",
                    "Preliminary entity analysis",
                    "Head of Surveillance notification",
                ],
                "timeline": "7 days",
                "approval_required": ApprovalAuthority.HEAD_OF_SURVEILLANCE,
                "escalation_notes": "Medium coordination risk requiring surveillance escalation and documentation",
            },
            RiskLevel.LOW: {
                "risk_score_range": (0.0, 3.9),
                "required_actions": [
                    "Routine monitoring continuation",
                    "Baseline threshold review",
                    "Periodic reassessment",
                    "Documentation for future reference",
                ],
                "timeline": "30 days",
                "approval_required": ApprovalAuthority.SENIOR_ANALYST,
                "escalation_notes": "Low coordination risk within normal monitoring parameters",
            },
        }

    def determine_escalation_level(
        self, risk_score: float, coordination_evidence: Dict, market_impact: float
    ) -> EscalationDecision:
        """
        Determine escalation level based on risk score and evidence.

        Args:
            risk_score: Overall coordination risk score (0-10)
            coordination_evidence: Dictionary with coordination evidence
            market_impact: Estimated market impact percentage

        Returns:
            EscalationDecision object with escalation details
        """
        try:
            # Adjust risk score based on market impact
            adjusted_risk_score = self._adjust_risk_score_for_market_impact(
                risk_score, market_impact
            )

            # Determine risk level
            risk_level = self._determine_risk_level(adjusted_risk_score)

            # Get escalation framework for this risk level
            framework = self.escalation_framework[risk_level]

            # Generate escalation decision
            escalation_decision = EscalationDecision(
                risk_level=risk_level,
                risk_score=adjusted_risk_score,
                required_actions=framework["required_actions"],
                timeline=framework["timeline"],
                approval_required=framework["approval_required"],
                escalation_notes=framework["escalation_notes"],
                decision_date=datetime.now().isoformat(),
            )

            return escalation_decision

        except Exception as e:
            self.logger.error(f"Error determining escalation level: {e}")
            return EscalationDecision(
                risk_level=RiskLevel.LOW,
                risk_score=0.0,
                required_actions=["Error in analysis - manual review required"],
                timeline="Immediate",
                approval_required=ApprovalAuthority.SENIOR_ANALYST,
                escalation_notes="Error in escalation analysis",
                decision_date=datetime.now().isoformat(),
            )

    def _adjust_risk_score_for_market_impact(
        self, risk_score: float, market_impact: float
    ) -> float:
        """Adjust risk score based on market impact."""
        try:
            # Market impact adjustment factor
            if market_impact > 0.2:  # >20% market impact
                adjustment_factor = 1.2
            elif market_impact > 0.1:  # >10% market impact
                adjustment_factor = 1.1
            else:
                adjustment_factor = 1.0

            adjusted_score = risk_score * adjustment_factor
            return min(10.0, adjusted_score)  # Cap at 10.0

        except Exception as e:
            self.logger.error(f"Error adjusting risk score: {e}")
            return risk_score

    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determine risk level based on adjusted risk score."""
        try:
            if risk_score >= 8.0:
                return RiskLevel.CRITICAL
            elif risk_score >= 6.0:
                return RiskLevel.HIGH
            elif risk_score >= 4.0:
                return RiskLevel.MEDIUM
            else:
                return RiskLevel.LOW

        except Exception as e:
            self.logger.error(f"Error determining risk level: {e}")
            return RiskLevel.LOW


class InvestigationProtocol:
    """
    Investigation Protocol for 21-Day Phased Investigation

    Implements the v1.4 standard investigation protocol with clear phases,
    objectives, deliverables, and success criteria.

    Economic Interpretation: Provides structured approach to coordination
    investigation with clear milestones and decision points.
    """

    def __init__(self):
        """Initialize investigation protocol with v1.4 standards."""
        self.protocol = self._initialize_investigation_protocol()
        self.logger = logging.getLogger(__name__)

    def _initialize_investigation_protocol(self) -> InvestigationProtocol:
        """Initialize investigation protocol with v1.4 standards."""
        phases = [
            InvestigationPhase(
                phase_number=1,
                phase_name="Evidence Gathering",
                duration_days=3,
                objectives=[
                    "Entity identification and preliminary KYC review",
                    "Communication pattern analysis where permissible",
                    "Cross-venue data correlation and validation",
                    "Initial evidence preservation and documentation",
                ],
                deliverables=[
                    "Entity identification report",
                    "Preliminary KYC assessment",
                    "Cross-venue data correlation analysis",
                    "Evidence preservation documentation",
                ],
                success_criteria=[
                    "All relevant entities identified",
                    "KYC review completed for top 5 entities",
                    "Cross-venue data validated and correlated",
                    "Evidence preservation protocol implemented",
                ],
                responsible_party="Head of Surveillance",
                escalation_triggers=[
                    "Insufficient entity identification",
                    "KYC review reveals high-risk entities",
                    "Data correlation shows systematic coordination",
                    "Evidence preservation issues identified",
                ],
            ),
            InvestigationPhase(
                phase_number=2,
                phase_name="Deep Investigation",
                duration_days=7,
                objectives=[
                    "Beneficial ownership verification through available channels",
                    "Economic impact quantification across extended periods",
                    "Legal review of evidence sufficiency and regulatory obligations",
                    "Communication analysis and algorithm documentation requests",
                ],
                deliverables=[
                    "Beneficial ownership verification report",
                    "Economic impact assessment",
                    "Legal sufficiency review",
                    "Communication pattern analysis",
                ],
                success_criteria=[
                    "Beneficial ownership verified for key entities",
                    "Economic impact quantified with confidence intervals",
                    "Legal sufficiency confirmed for regulatory reporting",
                    "Communication patterns analyzed and documented",
                ],
                responsible_party="Chief Risk Officer",
                escalation_triggers=[
                    "Beneficial ownership verification reveals complex structures",
                    "Economic impact exceeds regulatory thresholds",
                    "Legal review identifies regulatory reporting obligations",
                    "Communication analysis reveals systematic coordination",
                ],
            ),
            InvestigationPhase(
                phase_number=3,
                phase_name="Decision and Action",
                duration_days=11,
                objectives=[
                    "Executive review of investigation findings",
                    "Determination of regulatory notification requirements",
                    "Implementation of enhanced monitoring or enforcement referral",
                    "Documentation and case closure",
                ],
                deliverables=[
                    "Executive summary of investigation findings",
                    "Regulatory notification decision",
                    "Enhanced monitoring implementation plan",
                    "Case closure documentation",
                ],
                success_criteria=[
                    "Executive review completed with clear recommendations",
                    "Regulatory notification requirements determined",
                    "Enhanced monitoring or enforcement referral implemented",
                    "Case properly documented and closed",
                ],
                responsible_party="C-Suite",
                escalation_triggers=[
                    "Investigation findings require immediate regulatory notification",
                    "Enhanced monitoring reveals ongoing coordination",
                    "Enforcement referral required",
                    "Case complexity exceeds standard procedures",
                ],
            ),
        ]

        return InvestigationProtocol(
            total_duration_days=21,
            phases=phases,
            decision_points=[
                "Day 3: Evidence sufficiency assessment",
                "Day 10: Legal review and regulatory obligation determination",
                "Day 17: Executive review and decision",
                "Day 21: Final action implementation",
            ],
            escalation_matrix={},  # Will be populated by EscalationMatrix
            success_metrics={
                "evidence_completeness": 0.95,
                "legal_sufficiency": 0.90,
                "regulatory_compliance": 1.0,
                "case_resolution_time": 21.0,
            },
        )

    def get_investigation_plan(
        self, risk_level: RiskLevel, coordination_evidence: Dict
    ) -> InvestigationProtocol:
        """
        Get investigation plan based on risk level and evidence.

        Args:
            risk_level: Risk level from escalation matrix
            coordination_evidence: Dictionary with coordination evidence

        Returns:
            InvestigationProtocol object with customized plan
        """
        try:
            # Customize protocol based on risk level
            if risk_level == RiskLevel.CRITICAL:
                # Accelerate timeline for critical cases
                customized_phases = self._accelerate_timeline(self.protocol.phases, 0.5)
            elif risk_level == RiskLevel.HIGH:
                # Slightly accelerate timeline for high-risk cases
                customized_phases = self._accelerate_timeline(self.protocol.phases, 0.75)
            else:
                # Use standard timeline for medium and low-risk cases
                customized_phases = self.protocol.phases

            # Create customized protocol
            customized_protocol = InvestigationProtocol(
                total_duration_days=sum(phase.duration_days for phase in customized_phases),
                phases=customized_phases,
                decision_points=self.protocol.decision_points,
                escalation_matrix=self.protocol.escalation_matrix,
                success_metrics=self.protocol.success_metrics,
            )

            return customized_protocol

        except Exception as e:
            self.logger.error(f"Error getting investigation plan: {e}")
            return self.protocol

    def _accelerate_timeline(
        self, phases: List[InvestigationPhase], acceleration_factor: float
    ) -> List[InvestigationPhase]:
        """Accelerate investigation timeline based on risk level."""
        try:
            accelerated_phases = []

            for phase in phases:
                accelerated_duration = max(1, int(phase.duration_days * acceleration_factor))

                accelerated_phase = InvestigationPhase(
                    phase_number=phase.phase_number,
                    phase_name=phase.phase_name,
                    duration_days=accelerated_duration,
                    objectives=phase.objectives,
                    deliverables=phase.deliverables,
                    success_criteria=phase.success_criteria,
                    responsible_party=phase.responsible_party,
                    escalation_triggers=phase.escalation_triggers,
                )

                accelerated_phases.append(accelerated_phase)

            return accelerated_phases

        except Exception as e:
            self.logger.error(f"Error accelerating timeline: {e}")
            return phases


class DecisionMatrix:
    """
    Decision Matrix for Risk Score to Approval Authority Mapping

    Implements the v1.4 standard decision matrix linking risk scores
    to appropriate approval authorities and decision-making processes.

    Economic Interpretation: Ensures appropriate decision-making authority
    based on risk severity and potential market impact.
    """

    def __init__(self):
        """Initialize decision matrix with v1.4 standards."""
        self.decision_framework = self._initialize_decision_framework()
        self.logger = logging.getLogger(__name__)

    def _initialize_decision_framework(self) -> Dict[RiskLevel, Dict]:
        """Initialize decision framework with v1.4 standards."""
        return {
            RiskLevel.CRITICAL: {
                "approval_authority": ApprovalAuthority.C_SUITE,
                "decision_threshold": 8.0,
                "required_approvals": ["CEO", "CRO", "General Counsel"],
                "decision_timeframe": "24 hours",
                "escalation_path": "Immediate C-Suite notification",
                "regulatory_implications": "Potential regulatory notification required",
                "market_impact_threshold": 0.2,  # 20% market impact
            },
            RiskLevel.HIGH: {
                "approval_authority": ApprovalAuthority.CHIEF_RISK_OFFICER,
                "decision_threshold": 6.0,
                "required_approvals": ["CRO", "Head of Surveillance"],
                "decision_timeframe": "72 hours",
                "escalation_path": "CRO notification with C-Suite briefing",
                "regulatory_implications": "Enhanced monitoring and documentation",
                "market_impact_threshold": 0.1,  # 10% market impact
            },
            RiskLevel.MEDIUM: {
                "approval_authority": ApprovalAuthority.HEAD_OF_SURVEILLANCE,
                "decision_threshold": 4.0,
                "required_approvals": ["Head of Surveillance"],
                "decision_timeframe": "7 days",
                "escalation_path": "Standard surveillance escalation",
                "regulatory_implications": "Documentation and monitoring",
                "market_impact_threshold": 0.05,  # 5% market impact
            },
            RiskLevel.LOW: {
                "approval_authority": ApprovalAuthority.SENIOR_ANALYST,
                "decision_threshold": 0.0,
                "required_approvals": ["Senior Analyst"],
                "decision_timeframe": "30 days",
                "escalation_path": "Routine monitoring and documentation",
                "regulatory_implications": "Standard monitoring procedures",
                "market_impact_threshold": 0.01,  # 1% market impact
            },
        }

    def determine_approval_authority(
        self, risk_score: float, market_impact: float, coordination_evidence: Dict
    ) -> Dict:
        """
        Determine approval authority based on risk score and evidence.

        Args:
            risk_score: Overall coordination risk score (0-10)
            market_impact: Estimated market impact percentage
            coordination_evidence: Dictionary with coordination evidence

        Returns:
            Dictionary with approval authority and decision framework
        """
        try:
            # Determine risk level
            if risk_score >= 8.0:
                risk_level = RiskLevel.CRITICAL
            elif risk_score >= 6.0:
                risk_level = RiskLevel.HIGH
            elif risk_score >= 4.0:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW

            # Get decision framework for this risk level
            framework = self.decision_framework[risk_level]

            # Check if market impact requires escalation
            if market_impact > framework["market_impact_threshold"]:
                # Escalate to next higher authority
                escalated_framework = self._escalate_authority(framework, risk_level)
                framework = escalated_framework

            # Add risk score and evidence information
            framework["risk_score"] = risk_score
            framework["market_impact"] = market_impact
            framework["coordination_evidence"] = coordination_evidence
            framework["decision_date"] = datetime.now().isoformat()

            return framework

        except Exception as e:
            self.logger.error(f"Error determining approval authority: {e}")
            return {
                "approval_authority": ApprovalAuthority.SENIOR_ANALYST,
                "decision_threshold": 0.0,
                "required_approvals": ["Senior Analyst"],
                "decision_timeframe": "30 days",
                "escalation_path": "Error in analysis - manual review required",
                "regulatory_implications": "Standard monitoring procedures",
                "market_impact_threshold": 0.01,
                "risk_score": risk_score,
                "market_impact": market_impact,
                "coordination_evidence": coordination_evidence,
                "decision_date": datetime.now().isoformat(),
            }

    def _escalate_authority(self, framework: Dict, current_risk_level: RiskLevel) -> Dict:
        """Escalate approval authority based on market impact."""
        try:
            # Define escalation hierarchy
            escalation_hierarchy = {
                RiskLevel.LOW: RiskLevel.MEDIUM,
                RiskLevel.MEDIUM: RiskLevel.HIGH,
                RiskLevel.HIGH: RiskLevel.CRITICAL,
                RiskLevel.CRITICAL: RiskLevel.CRITICAL,  # Cannot escalate further
            }

            # Get escalated risk level
            escalated_risk_level = escalation_hierarchy[current_risk_level]

            # Get escalated framework
            escalated_framework = self.decision_framework[escalated_risk_level]

            return escalated_framework

        except Exception as e:
            self.logger.error(f"Error escalating authority: {e}")
            return framework


class OperationalIntegrationFramework:
    """
    Main framework for operational integration following v1.4 standards.

    Orchestrates all operational integration components and provides
    comprehensive operational framework for coordination detection.
    """

    def __init__(self):
        """Initialize operational integration framework."""
        self.escalation_matrix = EscalationMatrix()
        self.investigation_protocol = InvestigationProtocol()
        self.decision_matrix = DecisionMatrix()
        self.logger = logging.getLogger(__name__)

    def process_coordination_alert(
        self, risk_score: float, coordination_evidence: Dict, market_impact: float
    ) -> Dict:
        """
        Process coordination alert through complete operational framework.

        Args:
            risk_score: Overall coordination risk score (0-10)
            coordination_evidence: Dictionary with coordination evidence
            market_impact: Estimated market impact percentage

        Returns:
            Dictionary with complete operational response
        """
        try:
            # Determine escalation level
            escalation_decision = self.escalation_matrix.determine_escalation_level(
                risk_score, coordination_evidence, market_impact
            )

            # Get investigation plan
            investigation_plan = self.investigation_protocol.get_investigation_plan(
                escalation_decision.risk_level, coordination_evidence
            )

            # Determine approval authority
            approval_authority = self.decision_matrix.determine_approval_authority(
                risk_score, market_impact, coordination_evidence
            )

            # Compile operational response
            operational_response = {
                "escalation_decision": escalation_decision,
                "investigation_plan": investigation_plan,
                "approval_authority": approval_authority,
                "processing_date": datetime.now().isoformat(),
                "operational_status": "Alert Processed",
                "next_review_date": self._calculate_next_review_date(
                    escalation_decision.risk_level
                ),
            }

            return operational_response

        except Exception as e:
            self.logger.error(f"Error processing coordination alert: {e}")
            return {
                "escalation_decision": None,
                "investigation_plan": None,
                "approval_authority": None,
                "processing_date": datetime.now().isoformat(),
                "operational_status": "Error in Processing",
                "next_review_date": datetime.now().isoformat(),
            }

    def _calculate_next_review_date(self, risk_level: RiskLevel) -> str:
        """Calculate next review date based on risk level."""
        try:
            if risk_level == RiskLevel.CRITICAL:
                next_review = datetime.now() + timedelta(hours=24)
            elif risk_level == RiskLevel.HIGH:
                next_review = datetime.now() + timedelta(hours=72)
            elif risk_level == RiskLevel.MEDIUM:
                next_review = datetime.now() + timedelta(days=7)
            else:
                next_review = datetime.now() + timedelta(days=30)

            return next_review.isoformat()

        except Exception as e:
            self.logger.error(f"Error calculating next review date: {e}")
            return datetime.now().isoformat()


# Example usage and testing
if __name__ == "__main__":
    # Test operational integration framework
    framework = OperationalIntegrationFramework()

    # Test parameters
    risk_score = 8.1
    coordination_evidence = {
        "similarity_score": 0.76,
        "statistical_significance": 0.001,
        "entity_count": 5,
        "coordination_volume": 0.71,
    }
    market_impact = 0.15  # 15% market impact

    # Process coordination alert
    operational_response = framework.process_coordination_alert(
        risk_score, coordination_evidence, market_impact
    )

    print("Operational Integration Framework Results:")
    print(f"Risk Level: {operational_response['escalation_decision'].risk_level.value}")
    print(f"Risk Score: {operational_response['escalation_decision'].risk_score:.1f}")
    print(f"Timeline: {operational_response['escalation_decision'].timeline}")
    print(
        f"Approval Required: {operational_response['escalation_decision'].approval_required.value}"
    )
    print(
        f"Investigation Duration: {operational_response['investigation_plan'].total_duration_days} days"
    )
    print(f"Next Review Date: {operational_response['next_review_date']}")

    print("\nRequired Actions:")
    for action in operational_response["escalation_decision"].required_actions:
        print(f"  - {action}")

    print("\nInvestigation Phases:")
    for phase in operational_response["investigation_plan"].phases:
        print(f"  Phase {phase.phase_number}: {phase.phase_name} ({phase.duration_days} days)")
        print(f"    Responsible: {phase.responsible_party}")
        print(f"    Objectives: {len(phase.objectives)} objectives")
        print(f"    Deliverables: {len(phase.deliverables)} deliverables")

