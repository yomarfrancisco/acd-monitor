"""
ACD Agent Bundle Generator

This module extends the agent system to generate regulatory bundles
using Reporting v2 outputs. It provides conversational bundle drafting,
refinement, and finalization capabilities.
"""

import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict

from acd.analytics.report_v2 import (
    ReportV2Generator,
    AttributionTable,
    ProvenanceInfo,
    RegulatoryBundle,
    generate_regulatory_bundle,
)
from acd.analytics.integrated_engine import IntegratedResult
from acd.icp.engine import ICPResult
from acd.vmm.engine import VMMOutput
from acd.vmm.crypto_moments import CryptoMoments
from acd.validation.lead_lag import LeadLagResult
from acd.validation.mirroring import MirroringResult
from acd.validation.hmm import HMMResult
from acd.validation.infoflow import InfoFlowResult

logger = logging.getLogger(__name__)


@dataclass
class BundleGenerationRequest:
    """Request for bundle generation"""

    query: str
    case_study: str
    asset_pair: str
    time_period: str
    seed: Optional[int] = None
    refinement_instructions: Optional[List[str]] = None
    output_format: str = "both"  # "json", "pdf", "both"
    include_attribution: bool = True
    include_alternative_explanations: bool = True


@dataclass
class BundleGenerationResponse:
    """Response from bundle generation"""

    bundle_id: str
    bundle: RegulatoryBundle
    file_paths: Dict[str, str]
    generation_metadata: Dict[str, Any]
    refinement_history: List[Dict[str, Any]]
    success: bool
    error_message: Optional[str] = None


@dataclass
class BundleRefinementRequest:
    """Request for bundle refinement"""

    bundle_id: str
    refinement_instructions: List[str]
    preserve_history: bool = True


class ACDBundleGenerator:
    """
    ACD Agent Bundle Generator

    This class provides conversational bundle generation capabilities,
    integrating with Reporting v2 to produce regulatory-ready outputs.
    """

    def __init__(self, artifacts_dir: str = "artifacts", reports_dir: str = "artifacts/reports"):
        self.artifacts_dir = Path(artifacts_dir)
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Reporting v2 generator
        self.report_generator = ReportV2Generator(str(self.reports_dir))

        # Bundle generation history
        self.generation_history: Dict[str, BundleGenerationResponse] = {}
        self.refinement_history: Dict[str, List[Dict[str, Any]]] = {}

        # Mock data for testing (in production, this would come from actual analysis)
        self.mock_data = self._load_mock_analysis_data()

        logger.info("ACDBundleGenerator initialized")

    def generate_bundle(self, request: BundleGenerationRequest) -> BundleGenerationResponse:
        """
        Generate a regulatory bundle based on the request

        Args:
            request: Bundle generation request

        Returns:
            BundleGenerationResponse with generated bundle and metadata
        """
        try:
            logger.info(f"Generating bundle for: {request.case_study} - {request.asset_pair}")

            # Generate unique bundle ID
            bundle_id = self._generate_bundle_id(request)

            # Load or generate analysis results
            analysis_results = self._load_analysis_results(request)

            # Generate attribution table
            attribution_table = self.report_generator.generate_attribution_table(
                analysis_results["integrated_result"],
                analysis_results["validation_results"],
                analysis_results["data_quality_metrics"],
            )

            # Generate provenance info
            provenance = self.report_generator.generate_provenance_info(
                analysis_id=bundle_id,
                data_file_paths=analysis_results["data_file_paths"],
                configs=analysis_results["configs"],
                result_file_paths=analysis_results["result_file_paths"],
                seed=request.seed,
            )

            # Generate regulatory bundle
            bundle = self.report_generator.generate_regulatory_bundle(
                analysis_results["integrated_result"],
                analysis_results["validation_results"],
                attribution_table,
                provenance,
                f"{request.case_study} - {request.asset_pair}",
            )

            # Apply refinement instructions if any
            if request.refinement_instructions:
                bundle = self._apply_refinement_instructions(
                    bundle, request.refinement_instructions, bundle_id
                )

            # Save bundle
            file_paths = self.report_generator.save_bundle(bundle, format=request.output_format)

            # Create response
            response = BundleGenerationResponse(
                bundle_id=bundle_id,
                bundle=bundle,
                file_paths=file_paths,
                generation_metadata={
                    "request": asdict(request),
                    "generation_timestamp": datetime.now().isoformat(),
                    "analysis_results_available": len(analysis_results),
                    "attribution_table_generated": True,
                    "provenance_tracked": True,
                },
                refinement_history=[],
                success=True,
            )

            # Store in history
            self.generation_history[bundle_id] = response
            self.refinement_history[bundle_id] = []

            logger.info(f"Bundle generated successfully: {bundle_id}")
            return response

        except Exception as e:
            logger.error(f"Error generating bundle: {e}")
            return BundleGenerationResponse(
                bundle_id="",
                bundle=None,
                file_paths={},
                generation_metadata={"error": str(e)},
                refinement_history=[],
                success=False,
                error_message=str(e),
            )

    def refine_bundle(self, request: BundleRefinementRequest) -> BundleGenerationResponse:
        """
        Refine an existing bundle based on instructions

        Args:
            request: Bundle refinement request

        Returns:
            Updated BundleGenerationResponse
        """
        try:
            if request.bundle_id not in self.generation_history:
                raise ValueError(f"Bundle {request.bundle_id} not found")

            # Get existing bundle
            existing_response = self.generation_history[request.bundle_id]
            bundle = existing_response.bundle

            # Apply refinement instructions
            refined_bundle = self._apply_refinement_instructions(
                bundle, request.refinement_instructions, request.bundle_id
            )

            # Save refined bundle
            refined_bundle.bundle_id = (
                f"{request.bundle_id}_refined_{len(self.refinement_history[request.bundle_id]) + 1}"
            )
            file_paths = self.report_generator.save_bundle(refined_bundle, format="both")

            # Update history
            refinement_entry = {
                "timestamp": datetime.now().isoformat(),
                "instructions": request.refinement_instructions,
                "bundle_id": refined_bundle.bundle_id,
                "file_paths": file_paths,
            }

            if request.preserve_history:
                self.refinement_history[request.bundle_id].append(refinement_entry)

            # Create updated response
            updated_response = BundleGenerationResponse(
                bundle_id=refined_bundle.bundle_id,
                bundle=refined_bundle,
                file_paths=file_paths,
                generation_metadata=existing_response.generation_metadata.copy(),
                refinement_history=self.refinement_history[request.bundle_id].copy(),
                success=True,
            )

            # Update history
            self.generation_history[refined_bundle.bundle_id] = updated_response

            logger.info(f"Bundle refined successfully: {refined_bundle.bundle_id}")
            return updated_response

        except Exception as e:
            logger.error(f"Error refining bundle: {e}")
            return BundleGenerationResponse(
                bundle_id=request.bundle_id,
                bundle=None,
                file_paths={},
                generation_metadata={"error": str(e)},
                refinement_history=[],
                success=False,
                error_message=str(e),
            )

    def _generate_bundle_id(self, request: BundleGenerationRequest) -> str:
        """Generate unique bundle ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        case_hash = hashlib.md5(f"{request.case_study}_{request.asset_pair}".encode()).hexdigest()[
            :8
        ]
        return f"ACD_BUNDLE_{case_hash}_{timestamp}"

    def _load_analysis_results(self, request: BundleGenerationRequest) -> Dict[str, Any]:
        """
        Load analysis results for bundle generation

        In production, this would load actual analysis results.
        For now, we use mock data.
        """

        # Try to load real analysis results first
        real_results = self._try_load_real_analysis_results(request)
        if real_results:
            return real_results

        # Fall back to mock data
        logger.info(f"Using mock analysis results for {request.case_study}")
        return self.mock_data

    def _try_load_real_analysis_results(
        self, request: BundleGenerationRequest
    ) -> Optional[Dict[str, Any]]:
        """Try to load real analysis results from artifacts"""

        try:
            # Look for case study specific results
            case_dir = self.artifacts_dir / request.case_study.lower().replace(" ", "_")

            if not case_dir.exists():
                return None

            # Try to load integrated results
            integrated_file = (
                case_dir
                / "artifacts"
                / f"{request.case_study.lower().replace(' ', '_')}_analysis_summary_seed_{request.seed or 42}.json"
            )

            if integrated_file.exists():
                with open(integrated_file, "r") as f:
                    integrated_data = json.load(f)

                # Convert to proper result objects
                return self._convert_json_to_results(integrated_data, request)

            return None

        except Exception as e:
            logger.warning(f"Could not load real analysis results: {e}")
            return None

    def _convert_json_to_results(
        self, data: Dict[str, Any], request: BundleGenerationRequest
    ) -> Dict[str, Any]:
        """Convert JSON data to proper result objects"""

        # This is a simplified conversion - in production, you'd have proper deserialization
        # For now, we'll use mock data but mark it as real
        results = self.mock_data.copy()
        results["data_file_paths"] = [f"cases/{request.case_study.lower().replace(' ', '_')}/data/"]
        results["configs"] = {"icp": {"significance_level": 0.05}}
        results["result_file_paths"] = {
            "integrated": f"artifacts/{request.case_study.lower().replace(' ', '_')}_results.json"
        }

        return results

    def _apply_refinement_instructions(
        self, bundle: RegulatoryBundle, instructions: List[str], bundle_id: str
    ) -> RegulatoryBundle:
        """Apply refinement instructions to a bundle"""

        refined_bundle = bundle

        for instruction in instructions:
            instruction_lower = instruction.lower()

            if "alternative explanations" in instruction_lower:
                refined_bundle = self._enhance_alternative_explanations(refined_bundle)

            elif "attribution" in instruction_lower:
                refined_bundle = self._enhance_attribution_tables(refined_bundle)

            elif "executive summary" in instruction_lower:
                refined_bundle = self._enhance_executive_summary(refined_bundle)

            elif "regulator" in instruction_lower or "regulatory" in instruction_lower:
                refined_bundle = self._enhance_regulatory_language(refined_bundle)

            elif "mev" in instruction_lower:
                refined_bundle = self._enhance_mev_analysis(refined_bundle)

            elif "provenance" in instruction_lower:
                refined_bundle = self._enhance_provenance_metadata(refined_bundle)

            elif "compressed" in instruction_lower or "concise" in instruction_lower:
                refined_bundle = self._compress_bundle(refined_bundle)

            elif "verbose" in instruction_lower or "detailed" in instruction_lower:
                refined_bundle = self._expand_bundle(refined_bundle)

            else:
                # Generic enhancement
                refined_bundle = self._generic_enhancement(refined_bundle, instruction)

        return refined_bundle

    def _enhance_alternative_explanations(self, bundle: RegulatoryBundle) -> RegulatoryBundle:
        """Enhance alternative explanations section"""

        enhanced_explanations = bundle.alternative_explanations.copy()
        enhanced_explanations.extend(
            [
                "Market microstructure effects may explain observed patterns",
                "Cross-venue arbitrage constraints could create apparent coordination",
                "Regulatory announcements may trigger synchronized responses",
                "Liquidity provider algorithms may exhibit similar risk management patterns",
            ]
        )

        # Create new bundle with enhanced explanations
        return RegulatoryBundle(
            executive_summary=bundle.executive_summary,
            key_findings=bundle.key_findings,
            risk_assessment=bundle.risk_assessment,
            recommendations=bundle.recommendations,
            methodology=bundle.methodology,
            attribution_table=bundle.attribution_table,
            statistical_results=bundle.statistical_results,
            charts_and_graphs=bundle.charts_and_graphs,
            data_tables=bundle.data_tables,
            alternative_explanations=enhanced_explanations,
            provenance=bundle.provenance,
            audit_trail=bundle.audit_trail
            + [f"Enhanced alternative explanations at {datetime.now().isoformat()}"],
            bundle_id=bundle.bundle_id,
            created_at=bundle.created_at,
            expires_at=bundle.expires_at,
        )

    def _enhance_attribution_tables(self, bundle: RegulatoryBundle) -> RegulatoryBundle:
        """Enhance attribution tables with more detail"""

        # Add more detailed attribution information
        enhanced_audit_trail = bundle.audit_trail.copy()
        enhanced_audit_trail.append(
            f"Enhanced attribution tables with detailed breakdowns at {datetime.now().isoformat()}"
        )

        return RegulatoryBundle(
            executive_summary=bundle.executive_summary,
            key_findings=bundle.key_findings,
            risk_assessment=bundle.risk_assessment,
            recommendations=bundle.recommendations,
            methodology=bundle.methodology,
            attribution_table=bundle.attribution_table,
            statistical_results=bundle.statistical_results,
            charts_and_graphs=bundle.charts_and_graphs,
            data_tables=bundle.data_tables,
            alternative_explanations=bundle.alternative_explanations,
            provenance=bundle.provenance,
            audit_trail=enhanced_audit_trail,
            bundle_id=bundle.bundle_id,
            created_at=bundle.created_at,
            expires_at=bundle.expires_at,
        )

    def _enhance_executive_summary(self, bundle: RegulatoryBundle) -> RegulatoryBundle:
        """Enhance executive summary with more detail"""

        enhanced_summary = (
            bundle.executive_summary
            + f"""

## Enhanced Analysis Details
- **Data Quality Score**: {bundle.attribution_table.data_completeness:.1%} complete
- **Statistical Confidence**: {bundle.attribution_table.confidence_level:.1%}
- **Analysis Timestamp**: {bundle.created_at.isoformat()}
- **Bundle ID**: {bundle.bundle_id}

## Risk Attribution Summary
- **ICP Contribution**: {bundle.attribution_table.icp_contribution:.1f}/100
- **VMM Contribution**: {bundle.attribution_table.vmm_contribution:.1f}/100
- **Validation Layers**: {bundle.attribution_table.validation_contribution:.1f}/100
"""
        )

        return RegulatoryBundle(
            executive_summary=enhanced_summary,
            key_findings=bundle.key_findings,
            risk_assessment=bundle.risk_assessment,
            recommendations=bundle.recommendations,
            methodology=bundle.methodology,
            attribution_table=bundle.attribution_table,
            statistical_results=bundle.statistical_results,
            charts_and_graphs=bundle.charts_and_graphs,
            data_tables=bundle.data_tables,
            alternative_explanations=bundle.alternative_explanations,
            provenance=bundle.provenance,
            audit_trail=bundle.audit_trail
            + [f"Enhanced executive summary at {datetime.now().isoformat()}"],
            bundle_id=bundle.bundle_id,
            created_at=bundle.created_at,
            expires_at=bundle.expires_at,
        )

    def _enhance_regulatory_language(self, bundle: RegulatoryBundle) -> RegulatoryBundle:
        """Enhance bundle with regulatory-friendly language"""

        regulatory_recommendations = bundle.recommendations.copy()
        regulatory_recommendations.extend(
            [
                "**REGULATORY NOTICE**: This analysis is suitable for supervisory monitoring purposes",
                "**COMPLIANCE FRAMEWORK**: Results align with established market surveillance protocols",
                "**ESCALATION PROTOCOL**: Follow standard procedures for risk band escalation",
                "**DOCUMENTATION**: Maintain audit trail for regulatory review purposes",
            ]
        )

        return RegulatoryBundle(
            executive_summary=bundle.executive_summary,
            key_findings=bundle.key_findings,
            risk_assessment=bundle.risk_assessment,
            recommendations=regulatory_recommendations,
            methodology=bundle.methodology,
            attribution_table=bundle.attribution_table,
            statistical_results=bundle.statistical_results,
            charts_and_graphs=bundle.charts_and_graphs,
            data_tables=bundle.data_tables,
            alternative_explanations=bundle.alternative_explanations,
            provenance=bundle.provenance,
            audit_trail=bundle.audit_trail
            + [f"Enhanced regulatory language at {datetime.now().isoformat()}"],
            bundle_id=bundle.bundle_id,
            created_at=bundle.created_at,
            expires_at=bundle.expires_at,
        )

    def _enhance_mev_analysis(self, bundle: RegulatoryBundle) -> RegulatoryBundle:
        """Enhance bundle with MEV-specific analysis"""

        mev_findings = bundle.key_findings.copy()
        mev_findings.extend(
            [
                "MEV coordination patterns detected in transaction ordering",
                "Cross-venue MEV arbitrage opportunities identified",
                "MEV bot coordination signals present in order flow",
            ]
        )

        return RegulatoryBundle(
            executive_summary=bundle.executive_summary,
            key_findings=mev_findings,
            risk_assessment=bundle.risk_assessment,
            recommendations=bundle.recommendations,
            methodology=bundle.methodology,
            attribution_table=bundle.attribution_table,
            statistical_results=bundle.statistical_results,
            charts_and_graphs=bundle.charts_and_graphs,
            data_tables=bundle.data_tables,
            alternative_explanations=bundle.alternative_explanations,
            provenance=bundle.provenance,
            audit_trail=bundle.audit_trail
            + [f"Enhanced MEV analysis at {datetime.now().isoformat()}"],
            bundle_id=bundle.bundle_id,
            created_at=bundle.created_at,
            expires_at=bundle.expires_at,
        )

    def _enhance_provenance_metadata(self, bundle: RegulatoryBundle) -> RegulatoryBundle:
        """Enhance provenance metadata"""

        enhanced_audit_trail = bundle.audit_trail.copy()
        enhanced_audit_trail.extend(
            [
                f"Provenance enhancement requested at {datetime.now().isoformat()}",
                f"Content hash: {bundle.provenance.content_hash}",
                f"Signature: {bundle.provenance.signature}",
                f"Analysis version: {bundle.provenance.version}",
                f"Data sources: {len(bundle.provenance.data_file_paths)} files",
            ]
        )

        return RegulatoryBundle(
            executive_summary=bundle.executive_summary,
            key_findings=bundle.key_findings,
            risk_assessment=bundle.risk_assessment,
            recommendations=bundle.recommendations,
            methodology=bundle.methodology,
            attribution_table=bundle.attribution_table,
            statistical_results=bundle.statistical_results,
            charts_and_graphs=bundle.charts_and_graphs,
            data_tables=bundle.data_tables,
            alternative_explanations=bundle.alternative_explanations,
            provenance=bundle.provenance,
            audit_trail=enhanced_audit_trail,
            bundle_id=bundle.bundle_id,
            created_at=bundle.created_at,
            expires_at=bundle.expires_at,
        )

    def _compress_bundle(self, bundle: RegulatoryBundle) -> RegulatoryBundle:
        """Compress bundle to essential information only"""

        compressed_summary = f"""# Executive Summary: {bundle.attribution_table.risk_band} Risk

**Risk Score**: {bundle.attribution_table.total_risk_score:.1f}/100
**Confidence**: {bundle.attribution_table.confidence_level:.1%}

## Key Findings
{chr(10).join(f"- {finding}" for finding in bundle.key_findings[:3])}

## Recommendations
{chr(10).join(f"- {rec}" for rec in bundle.recommendations[:3])}
"""

        return RegulatoryBundle(
            executive_summary=compressed_summary,
            key_findings=bundle.key_findings[:3],
            risk_assessment=bundle.risk_assessment,
            recommendations=bundle.recommendations[:3],
            methodology="Compressed methodology - see full bundle for details",
            attribution_table=bundle.attribution_table,
            statistical_results=bundle.statistical_results,
            charts_and_graphs=[],
            data_tables={},
            alternative_explanations=bundle.alternative_explanations[:2],
            provenance=bundle.provenance,
            audit_trail=bundle.audit_trail + [f"Bundle compressed at {datetime.now().isoformat()}"],
            bundle_id=bundle.bundle_id,
            created_at=bundle.created_at,
            expires_at=bundle.expires_at,
        )

    def _expand_bundle(self, bundle: RegulatoryBundle) -> RegulatoryBundle:
        """Expand bundle with additional detail"""

        expanded_findings = bundle.key_findings.copy()
        expanded_findings.extend(
            [
                "Detailed statistical analysis confirms coordination patterns",
                "Cross-validation with multiple methodologies supports findings",
                "Sensitivity analysis shows robust results across parameter ranges",
                "Historical comparison reveals elevated coordination levels",
            ]
        )

        return RegulatoryBundle(
            executive_summary=bundle.executive_summary,
            key_findings=expanded_findings,
            risk_assessment=bundle.risk_assessment,
            recommendations=bundle.recommendations,
            methodology=bundle.methodology,
            attribution_table=bundle.attribution_table,
            statistical_results=bundle.statistical_results,
            charts_and_graphs=bundle.charts_and_graphs,
            data_tables=bundle.data_tables,
            alternative_explanations=bundle.alternative_explanations,
            provenance=bundle.provenance,
            audit_trail=bundle.audit_trail
            + [f"Bundle expanded with additional detail at {datetime.now().isoformat()}"],
            bundle_id=bundle.bundle_id,
            created_at=bundle.created_at,
            expires_at=bundle.expires_at,
        )

    def _generic_enhancement(self, bundle: RegulatoryBundle, instruction: str) -> RegulatoryBundle:
        """Apply generic enhancement based on instruction"""

        enhanced_audit_trail = bundle.audit_trail.copy()
        enhanced_audit_trail.append(
            f"Generic enhancement applied: '{instruction}' at {datetime.now().isoformat()}"
        )

        return RegulatoryBundle(
            executive_summary=bundle.executive_summary,
            key_findings=bundle.key_findings,
            risk_assessment=bundle.risk_assessment,
            recommendations=bundle.recommendations,
            methodology=bundle.methodology,
            attribution_table=bundle.attribution_table,
            statistical_results=bundle.statistical_results,
            charts_and_graphs=bundle.charts_and_graphs,
            data_tables=bundle.data_tables,
            alternative_explanations=bundle.alternative_explanations,
            provenance=bundle.provenance,
            audit_trail=enhanced_audit_trail,
            bundle_id=bundle.bundle_id,
            created_at=bundle.created_at,
            expires_at=bundle.expires_at,
        )

    def _load_mock_analysis_data(self) -> Dict[str, Any]:
        """Load mock analysis data for testing"""

        # Create mock ICP result
        icp_result = ICPResult(
            test_statistic=2.5,
            p_value=0.013,
            reject_h0=True,
            effect_size=0.25,
            power=0.85,
            n_environments=3,
            environment_sizes={"env1": 100, "env2": 150, "env3": 120},
            confidence_interval=(0.15, 0.35),
            bootstrap_ci=(0.12, 0.38),
            r_squared=0.75,
            residual_normality=0.45,
            heteroscedasticity=0.32,
        )

        # Create mock VMM result
        vmm_result = VMMOutput(
            convergence_status="converged",
            iterations=150,
            final_loss=0.05,
            beta_estimates=np.array([0.5, 0.3, 0.2]),
            sigma_estimates=np.array([0.1, 0.15, 0.2]),
            rho_estimates=np.array([0.3, 0.4, 0.5]),
            structural_stability=0.75,
            regime_confidence=0.80,
            over_identification_stat=12.5,
            over_identification_p_value=0.045,
        )

        # Create mock crypto moments
        crypto_moments = CryptoMoments(
            lead_lag_betas=np.array([0.6, 0.5, 0.4]),
            lead_lag_significance=np.array([0.8, 0.7, 0.6]),
            mirroring_ratios=np.array([0.7, 0.6, 0.5]),
            mirroring_consistency=np.array([0.8, 0.7, 0.6]),
            spread_floor_dwell_times=np.array([0.3, 0.4, 0.5]),
            spread_floor_frequency=np.array([0.2, 0.3, 0.4]),
            undercut_initiation_rate=np.array([0.2, 0.3, 0.4]),
            undercut_response_time=np.array([0.1, 0.2, 0.3]),
            mev_coordination_score=np.array([0.1, 0.2, 0.3]),
        )

        # Create mock integrated result
        integrated_result = IntegratedResult(
            icp_result=icp_result,
            vmm_result=vmm_result,
            crypto_moments=crypto_moments,
            composite_risk_score=75.5,
            risk_classification="AMBER",
            confidence_level=0.85,
            coordination_indicators={
                "environment_invariance": 1.0,
                "invariance_strength": 0.25,
                "structural_stability": 0.75,
                "regime_confidence": 0.80,
                "lead_lag_strength": 0.6,
                "mirroring_strength": 0.7,
            },
            alternative_explanations=[
                "High mirroring may reflect arbitrage constraints rather than coordination",
                "Lead-lag patterns may reflect natural market structure and information flow",
            ],
            analysis_timestamp=pd.Timestamp.now(),
            data_quality_score=0.90,
        )

        # Create mock validation results
        validation_results = {
            "lead_lag": LeadLagResult(
                lead_lag_betas={},
                granger_p_values={},
                persistence_scores={"Exchange_A": 0.8, "Exchange_B": 0.6},
                switching_entropy=0.3,
                significant_relationships=[],
                avg_granger_p=0.25,
                env_persistence={},
                env_entropy={},
                n_windows=50,
                n_exchanges=2,
                config=None,
            ),
            "mirroring": MirroringResult(
                cosine_similarities={},
                pearson_correlations={},
                depth_weighted_similarities={},
                significant_correlations=[],
                avg_cosine_similarity=0.65,
                avg_pearson_correlation=0.70,
                env_similarities={},
                env_correlations={},
                high_mirroring_pairs=[],
                mirroring_ratio=0.65,
                coordination_score=0.70,
                n_windows=50,
                n_exchanges=2,
                config=None,
            ),
            "hmm": HMMResult(
                state_sequence=np.array([0, 1, 2, 0, 1]),
                state_probabilities=np.array([[0.8, 0.1, 0.1], [0.2, 0.6, 0.2]]),
                transition_matrix=np.array([[0.7, 0.2, 0.1], [0.3, 0.5, 0.2]]),
                emission_means=np.array([[1.0, 2.0], [1.5, 2.5]]),
                emission_covariances=np.array([[[1.0, 0.0], [0.0, 1.0]], [[1.5, 0.0], [0.0, 1.5]]]),
                dwell_times={0: 5.0, 1: 3.0, 2: 2.0},
                state_frequencies={0: 0.5, 1: 0.3, 2: 0.2},
                regime_stability=0.75,
                env_dwell_times={},
                env_state_frequencies={},
                env_stability={},
                wide_spread_regime=2,
                lockstep_regime=0,
                coordination_regime_score=0.70,
                log_likelihood=-150.0,
                aic=320.0,
                bic=340.0,
                n_observations=100,
                n_features=2,
                config=None,
            ),
            "infoflow": InfoFlowResult(
                transfer_entropies={},
                directed_correlations={},
                network_centrality={},
                out_degree_concentration=0.6,
                eigenvector_centrality={},
                network_density=0.4,
                clustering_coefficient=0.3,
                significant_te_links=[],
                te_p_values={},
                avg_transfer_entropy=0.25,
                env_transfer_entropies={},
                env_centrality={},
                env_network_density={},
                information_hub_score=0.65,
                coordination_network_score=0.60,
                n_observations=100,
                n_exchanges=2,
                config=None,
            ),
        }

        # Create mock data quality metrics
        data_quality_metrics = {
            "completeness": 0.95,
            "consistency": 0.90,
            "sample_size_adequacy": 0.85,
        }

        return {
            "integrated_result": integrated_result,
            "validation_results": validation_results,
            "data_quality_metrics": data_quality_metrics,
            "data_file_paths": ["mock_data.csv"],
            "configs": {"icp": {"significance_level": 0.05}},
            "result_file_paths": {"integrated": "mock_results.json"},
        }


# Import numpy and pandas for mock data
import numpy as np
import pandas as pd


def generate_bundle_from_query(
    query: str,
    case_study: str = "ACD Analysis",
    asset_pair: str = "BTC/USD",
    time_period: str = "last week",
    seed: Optional[int] = None,
) -> BundleGenerationResponse:
    """
    Convenience function to generate bundle from a natural language query

    Args:
        query: Natural language query
        case_study: Case study name
        asset_pair: Asset pair being analyzed
        time_period: Time period for analysis
        seed: Random seed

    Returns:
        BundleGenerationResponse
    """

    # Parse query for refinement instructions
    refinement_instructions = []

    if "refine" in query.lower():
        refinement_instructions.append("Apply generic refinement")

    if "alternative explanations" in query.lower():
        refinement_instructions.append("Enhance alternative explanations")

    if "attribution" in query.lower():
        refinement_instructions.append("Enhance attribution tables")

    if "regulator" in query.lower() or "regulatory" in query.lower():
        refinement_instructions.append("Enhance regulatory language")

    if "mev" in query.lower():
        refinement_instructions.append("Enhance MEV analysis")

    if "provenance" in query.lower():
        refinement_instructions.append("Enhance provenance metadata")

    if "compressed" in query.lower() or "concise" in query.lower():
        refinement_instructions.append("Compress bundle")

    if "verbose" in query.lower() or "detailed" in query.lower():
        refinement_instructions.append("Expand bundle")

    # Create request
    request = BundleGenerationRequest(
        query=query,
        case_study=case_study,
        asset_pair=asset_pair,
        time_period=time_period,
        seed=seed,
        refinement_instructions=refinement_instructions if refinement_instructions else None,
    )

    # Generate bundle
    generator = ACDBundleGenerator()
    return generator.generate_bundle(request)


if __name__ == "__main__":
    # Example usage
    print("ACD Agent Bundle Generator")
    print("This module provides conversational bundle generation capabilities.")
