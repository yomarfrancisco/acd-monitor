#!/usr/bin/env python3
"""
CLI script for ad-hoc timestamping of ACD Monitor evidence bundles.

Usage:
    python scripts/timestamp_bundle.py --bundle <path>
    python scripts/timestamp_bundle.py --bundle <path> --verify
    python scripts/timestamp_bundle.py --bundle <path> --status
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from acd.evidence.bundle import EvidenceBundle
from acd.evidence.timestamping import create_timestamp_client

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_bundle(bundle_path: Path) -> EvidenceBundle:
    """Load an evidence bundle from file."""
    try:
        with open(bundle_path, "r") as f:
            bundle_data = json.load(f)

        # Create EvidenceBundle object
        bundle = EvidenceBundle(
            bundle_id=bundle_data.get("bundle_id", ""),
            creation_timestamp=bundle_data.get("creation_timestamp", ""),
            analysis_window_start=bundle_data.get("analysis_window_start", ""),
            analysis_window_end=bundle_data.get("analysis_window_end", ""),
            market=bundle_data.get("market", ""),
            vmm_outputs=bundle_data.get("vmm_outputs", {}),
            calibration_artifacts=bundle_data.get("calibration_artifacts", []),
            data_quality=bundle_data.get("data_quality", {}),
            vmm_config=bundle_data.get("vmm_config", {}),
            data_sources=bundle_data.get("data_sources", []),
            golden_dataset_validation=bundle_data.get("golden_dataset_validation", {}),
            reproducibility_metrics=bundle_data.get("reproducibility_metrics", {}),
            analyst=bundle_data.get("analyst", ""),
            version=bundle_data.get("version", ""),
            checksum=bundle_data.get("checksum", ""),
            adaptive_threshold_profile=bundle_data.get("adaptive_threshold_profile"),
            timestamp_chain=bundle_data.get("timestamp_chain"),
            quality_profile=bundle_data.get("quality_profile"),
        )

        return bundle

    except Exception as e:
        logger.error(f"Failed to load bundle from {bundle_path}: {e}")
        raise


def timestamp_bundle(bundle: EvidenceBundle, output_path: Path) -> None:
    """Timestamp an evidence bundle and save the updated version."""
    try:
        # Create timestamp client
        timestamp_client = create_timestamp_client()

        # Get bundle data for timestamping
        bundle_json = bundle.to_json()
        bundle_data = bundle_json.encode("utf-8")

        # Get existing checksum or compute new one
        bundle_checksum = bundle.checksum or bundle._compute_checksum()

        # Get timestamp
        logger.info(f"Requesting timestamp for bundle {bundle.bundle_id}")
        timestamp_chain = timestamp_client.timestamp_bundle(bundle_data, bundle_checksum)

        # Update bundle with timestamp chain
        bundle.timestamp_chain = timestamp_chain

        # Save updated bundle
        bundle.to_json(output_path)

        logger.info(f"Successfully timestamped bundle and saved to {output_path}")

        # Display timestamp information
        latest_timestamp = timestamp_chain.get_latest_timestamp()
        if latest_timestamp:
            print("✅ Bundle timestamped successfully!")
            print(f"   Timestamp: {latest_timestamp.isoformat()}")
            print(f"   Provider: {timestamp_chain.timestamp_responses[0].provider_name}")
            print(
                f"   Response time: {timestamp_chain.timestamp_responses[0].response_time_ms:.2f}ms"
            )

    except Exception as e:
        logger.error(f"Failed to timestamp bundle: {e}")
        raise


def verify_timestamp(bundle: EvidenceBundle) -> None:
    """Verify the timestamp chain of a bundle."""
    if not bundle.timestamp_chain:
        print("❌ No timestamp chain found in bundle")
        return

    try:
        # Handle both TimestampChain objects and dictionaries
        if hasattr(bundle.timestamp_chain, "verify_chain"):
            # It's a TimestampChain object
            verification_result = bundle.timestamp_chain.verify_chain()
        else:
            # It's a dictionary loaded from JSON
            print("📋 Timestamp chain information:")
            timestamp_chain = bundle.timestamp_chain
            print(f"   Bundle checksum: {timestamp_chain.get('bundle_checksum', 'N/A')}")
            print(f"   Timestamp created: {timestamp_chain.get('timestamp_created', 'N/A')}")

            responses = timestamp_chain.get("timestamp_responses", [])
            print(f"   Number of responses: {len(responses)}")

            for i, response in enumerate(responses):
                print(f"   Response {i+1}:")
                print(f"     Provider: {response.get('provider_name', 'N/A')}")
                print(f"     Timestamp: {response.get('timestamp', 'N/A')}")
                print(f"     Policy OID: {response.get('policy_oid', 'N/A')}")
                print(f"     Serial: {response.get('serial_number', 'N/A')}")
                print(f"     Status: {response.get('status', 'N/A')}")
                print(f"     Response time: {response.get('response_time_ms', 'N/A')}ms")

            print("✅ Timestamp chain information displayed successfully!")
            return

        if verification_result["valid"]:
            print("✅ Timestamp chain verification successful!")
            print(f"   Chain length: {verification_result['chain_length']}")

            for response in verification_result["responses"]:
                print(f"   - {response['provider']}: {response['timestamp']}")
                print(f"     Policy OID: {response['policy_oid']}")
                print(f"     Serial: {response['serial_number']}")
        else:
            print("❌ Timestamp chain verification failed!")
            for response in verification_result["responses"]:
                if not response.get("valid", True):
                    print(f"   - {response['provider']}: {response.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"Failed to verify timestamp chain: {e}")
        print(f"❌ Timestamp verification failed: {e}")


def show_provider_status() -> None:
    """Show status of all TSA providers."""
    try:
        timestamp_client = create_timestamp_client()
        status = timestamp_client.get_provider_status()

        print("🔍 TSA Provider Status:")
        print("=" * 50)

        for provider_name, provider_status in status.items():
            state_icon = (
                "🟢"
                if provider_status["state"] == "CLOSED"
                else "🔴" if provider_status["state"] == "OPEN" else "🟡"
            )
            print(f"{state_icon} {provider_name}")
            print(f"   Priority: {provider_status['priority']}")
            print(f"   State: {provider_status['state']}")
            print(f"   Failures: {provider_status['failure_count']}")
            print(f"   URL: {provider_status['url']}")
            print()

    except Exception as e:
        logger.error(f"Failed to get provider status: {e}")
        print(f"❌ Failed to get provider status: {e}")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Timestamp ACD Monitor evidence bundles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/timestamp_bundle.py --bundle demo/outputs/demo_bundle.json
  python scripts/timestamp_bundle.py --bundle demo_bundle.json --verify
  python scripts/timestamp_bundle.py --bundle demo_bundle.json --status
  python scripts/timestamp_bundle.py --providers
        """,
    )

    parser.add_argument("--bundle", "-b", type=Path, help="Path to evidence bundle file")

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output path for timestamped bundle (default: overwrite input)",
    )

    parser.add_argument(
        "--verify", "-v", action="store_true", help="Verify existing timestamp chain"
    )

    parser.add_argument("--status", "-s", action="store_true", help="Show TSA provider status")

    parser.add_argument("--providers", action="store_true", help="Show status of all TSA providers")

    args = parser.parse_args()

    try:
        if args.providers:
            show_provider_status()
            return

        if not args.bundle:
            parser.error("--bundle is required unless using --providers")

        if not args.bundle.exists():
            parser.error(f"Bundle file not found: {args.bundle}")

        # Load bundle
        bundle = load_bundle(args.bundle)

        if args.verify:
            verify_timestamp(bundle)
            return

        if args.status:
            show_provider_status()
            return

        # Determine output path
        output_path = args.output or args.bundle

        # Timestamp the bundle
        timestamp_bundle(bundle, output_path)

    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        print(f"❌ Operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
