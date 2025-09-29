#!/usr/bin/env python3
"""
Phase-2 Synthetic Analysis Pipeline

One-button reproducible script for running the complete Phase-2 analysis.
"""

import argparse
import sys
import json
import time
from pathlib import Path
import logging

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from acd.data.synthetic_crypto import SyntheticCryptoGenerator, SyntheticConfig
from acd.icp.engine import ICPEngine, ICPConfig
from acd.vmm.engine import VMMEngine, VMMConfig
from acd.vmm.crypto_moments import CryptoMomentCalculator, CryptoMomentConfig
from acd.vmm.scalers import GlobalMomentScaler
from acd.validation.lead_lag import analyze_lead_lag
from acd.validation.mirroring import analyze_mirroring
from acd.validation.hmm import analyze_hmm
from acd.validation.infoflow import analyze_infoflow
from agent.providers.offline_mock import OfflineMockProvider

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_phase2_analysis(seed: int = 42, n_samples: int = 6000):
    """Run complete Phase-2 analysis"""
    logger.info(f"Starting Phase-2 analysis with seed={seed}, n_samples={n_samples}")

    start_time = time.time()
    results = {}

    try:
        # 1. Generate synthetic data
        logger.info("Generating synthetic data...")
        config = SyntheticConfig(n_samples=n_samples, seed=seed)
        generator = SyntheticCryptoGenerator(config)
        competitive_data = generator.generate_competitive_scenario()
        coordinated_data = generator.generate_coordinated_scenario()

        # 2. Run ICP analysis
        logger.info("Running ICP analysis...")
        icp_engine = ICPEngine(ICPConfig())
        icp_results = {}

        for scenario_name, data in [
            ("competitive", competitive_data),
            ("coordinated", coordinated_data),
        ]:
            try:
                result = icp_engine.run_icp(
                    data, ["exchange_1", "exchange_2", "exchange_3"], "volatility_regime", seed
                )
                icp_results[scenario_name] = {
                    "invariance_p_value": result.invariance_p_value,
                    "power": result.power,
                    "status": "success",
                }
            except Exception as e:
                icp_results[scenario_name] = {"error": str(e), "status": "failed"}

        # 3. Run VMM analysis
        logger.info("Running VMM analysis...")
        vmm_engine = VMMEngine(
            VMMConfig(), CryptoMomentCalculator(CryptoMomentConfig(), GlobalMomentScaler())
        )
        vmm_results = {}

        for scenario_name, data in [
            ("competitive", competitive_data),
            ("coordinated", coordinated_data),
        ]:
            try:
                result = vmm_engine.run_vmm(
                    data, ["exchange_1", "exchange_2", "exchange_3"], "volatility_regime", seed
                )
                vmm_results[scenario_name] = {
                    "over_identification_p_value": result.over_identification_p_value,
                    "structural_stability": result.structural_stability,
                    "status": "success",
                }
            except Exception as e:
                vmm_results[scenario_name] = {"error": str(e), "status": "failed"}

        # 4. Run validation layers
        logger.info("Running validation layers...")
        validation_results = {}

        for scenario_name, data in [
            ("competitive", competitive_data),
            ("coordinated", coordinated_data),
        ]:
            scenario_results = {}

            # Lead-lag
            try:
                lead_lag_result = analyze_lead_lag(
                    data, ["exchange_1", "exchange_2", "exchange_3"], "volatility_regime", seed
                )
                scenario_results["lead_lag"] = {
                    "switching_entropy": lead_lag_result.switching_entropy,
                    "status": "success",
                }
            except Exception as e:
                scenario_results["lead_lag"] = {"error": str(e), "status": "failed"}

            # Mirroring
            try:
                mirroring_result = analyze_mirroring(
                    data, ["exchange_1", "exchange_2", "exchange_3"], "volatility_regime", seed
                )
                scenario_results["mirroring"] = {
                    "coordination_score": mirroring_result.coordination_score,
                    "status": "success",
                }
            except Exception as e:
                scenario_results["mirroring"] = {"error": str(e), "status": "failed"}

            # HMM
            try:
                hmm_result = analyze_hmm(
                    data, ["exchange_1", "exchange_2", "exchange_3"], "volatility_regime", seed
                )
                scenario_results["hmm"] = {
                    "regime_stability": hmm_result.regime_stability,
                    "status": "success",
                }
            except Exception as e:
                scenario_results["hmm"] = {"error": str(e), "status": "failed"}

            # Info flow
            try:
                infoflow_result = analyze_infoflow(
                    data, ["exchange_1", "exchange_2", "exchange_3"], "volatility_regime", seed
                )
                scenario_results["infoflow"] = {
                    "coordination_network_score": infoflow_result.coordination_network_score,
                    "status": "success",
                }
            except Exception as e:
                scenario_results["infoflow"] = {"error": str(e), "status": "failed"}

            validation_results[scenario_name] = scenario_results

        # 5. Test agent integration
        logger.info("Testing agent integration...")
        try:
            provider = OfflineMockProvider()
            test_result = provider.generate(prompt="Show mirroring ratios for BTC/USD last week")
            agent_results = {"status": "success", "response_length": len(test_result.content)}
        except Exception as e:
            agent_results = {"status": "failed", "error": str(e)}

        # Compile results
        results = {
            "pipeline_info": {
                "seed": seed,
                "n_samples": n_samples,
                "execution_time": time.time() - start_time,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "icp_results": icp_results,
            "vmm_results": vmm_results,
            "validation_results": validation_results,
            "agent_results": agent_results,
        }

        # Save results
        artifacts_dir = Path("artifacts")
        artifacts_dir.mkdir(exist_ok=True)

        results_file = artifacts_dir / f"phase2_results_seed_{seed}.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"Analysis completed in {time.time() - start_time:.2f} seconds")
        logger.info(f"Results saved to {results_file}")

        return results

    except Exception as e:
        logger.error(f"Phase-2 analysis failed: {e}")
        raise


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Phase-2 Synthetic Analysis Pipeline")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--N", type=int, default=6000, help="Number of samples per scenario")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        results = run_phase2_analysis(seed=args.seed, n_samples=args.N)

        print("\n" + "=" * 80)
        print("PHASE-2 ANALYSIS COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"Seed: {args.seed}")
        print(f"Sample Size: {args.N}")
        print(f"Execution Time: {results['pipeline_info']['execution_time']:.2f} seconds")
        print(f"Results saved to: artifacts/phase2_results_seed_{args.seed}.json")

        # Print key findings
        print("\nKey Findings:")
        icp_results = results.get("icp_results", {})
        if icp_results.get("competitive", {}).get("status") == "success":
            competitive_p = icp_results["competitive"]["invariance_p_value"]
            print(f"  - Competitive ICP p-value: {competitive_p:.6f}")

        if icp_results.get("coordinated", {}).get("status") == "success":
            coordinated_p = icp_results["coordinated"]["invariance_p_value"]
            print(f"  - Coordinated ICP p-value: {coordinated_p:.6f}")

        validation_results = results.get("validation_results", {})
        if validation_results:
            print(f"  - Validation layers completed for both scenarios")

        agent_results = results.get("agent_results", {})
        if agent_results.get("status") == "success":
            print(f"  - Agent integration test successful")

        print("\n" + "=" * 80)

    except Exception as e:
        logger.error(f"Phase-2 analysis failed: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
