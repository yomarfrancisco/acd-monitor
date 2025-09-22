#!/usr/bin/env python3
"""
ACD Agent CLI

Command-line interface for testing agent providers and queries.
Supports both Chatbase and offline providers for manual QA.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from agent.providers.chatbase_adapter import ChatbaseAdapter, create_provider, check_provider_health
from agent.providers.offline_mock import OfflineMockProvider
from agent.retrieval.loader import ACDArtifactLoader
from agent.retrieval.select import ACDArtifactSelector
from agent.compose.answer import ACDAnswerComposer


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="ACD Agent CLI for testing providers and queries")

    # Provider selection
    parser.add_argument(
        "--provider",
        choices=["chatbase", "offline"],
        default="offline",
        help="Provider to use (default: offline)",
    )

    # Query options
    parser.add_argument("--query", type=str, help="Query to send to the agent")

    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")

    # Health check
    parser.add_argument("--health", action="store_true", help="Check provider health")

    # Artifact operations
    parser.add_argument("--list-artifacts", action="store_true", help="List available artifacts")

    parser.add_argument(
        "--artifacts-dir",
        type=str,
        default="artifacts",
        help="Artifacts directory path (default: artifacts)",
    )

    # Output options
    parser.add_argument(
        "--output", choices=["text", "json"], default="text", help="Output format (default: text)"
    )

    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    try:
        if args.health:
            check_health(args)
        elif args.list_artifacts:
            list_artifacts(args)
        elif args.query:
            run_query(args)
        elif args.interactive:
            run_interactive(args)
        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def check_health(args):
    """Check provider health"""
    print(f"Checking health for provider: {args.provider}")

    if args.provider == "chatbase":
        health = check_provider_health("chatbase")
    else:
        provider = OfflineMockProvider(artifacts_dir=args.artifacts_dir)
        health = provider.healthcheck()

    if args.output == "json":
        print(
            json.dumps(
                {
                    "provider": args.provider,
                    "status": health.status,
                    "details": health.details,
                    "last_check": health.last_check,
                },
                indent=2,
            )
        )
    else:
        print(f"Status: {health.status}")
        print(f"Details: {json.dumps(health.details, indent=2)}")
        print(f"Last Check: {health.last_check}")


def list_artifacts(args):
    """List available artifacts"""
    print(f"Listing artifacts from: {args.artifacts_dir}")

    loader = ACDArtifactLoader(args.artifacts_dir)
    artifacts = loader.list_available_artifacts()

    if args.output == "json":
        print(json.dumps(artifacts, indent=2))
    else:
        for artifact_type, file_paths in artifacts.items():
            print(f"\n{artifact_type.upper()}:")
            for file_path in file_paths:
                print(f"  - {file_path}")


def run_query(args):
    """Run a single query"""
    print(f"Running query with provider: {args.provider}")
    print(f"Query: {args.query}")
    print("-" * 50)

    # Create provider
    if args.provider == "chatbase":
        provider = create_provider("chatbase")
    else:
        provider = OfflineMockProvider(artifacts_dir=args.artifacts_dir)

    # Run query
    result = provider.generate(prompt=args.query, session_id=f"cli_session_{args.provider}")

    # Output result
    if args.output == "json":
        output = {
            "provider": args.provider,
            "query": args.query,
            "response": {
                "content": result.content,
                "session_id": result.session_id,
                "usage": result.usage,
                "metadata": result.metadata,
            },
        }
        print(json.dumps(output, indent=2))
    else:
        print("RESPONSE:")
        print(result.content)
        print("\n" + "-" * 50)
        print("METADATA:")
        print(f"Session ID: {result.session_id}")
        print(f"Usage: {json.dumps(result.usage, indent=2)}")
        if args.verbose:
            print(f"Metadata: {json.dumps(result.metadata, indent=2)}")


def run_interactive(args):
    """Run in interactive mode"""
    print(f"Interactive mode with provider: {args.provider}")
    print("Type 'quit' or 'exit' to stop, 'help' for commands")
    print("-" * 50)

    # Create provider
    if args.provider == "chatbase":
        provider = create_provider("chatbase")
    else:
        provider = OfflineMockProvider(artifacts_dir=args.artifacts_dir)

    # Create artifact components for offline provider
    if args.provider == "offline":
        loader = ACDArtifactLoader(args.artifacts_dir)
        selector = ACDArtifactSelector(args.artifacts_dir)
        composer = ACDAnswerComposer()

    session_id = f"interactive_{args.provider}"

    while True:
        try:
            query = input("\n> ").strip()

            if query.lower() in ["quit", "exit"]:
                break
            elif query.lower() == "help":
                print_help()
                continue
            elif query.lower() == "health":
                health = provider.healthcheck()
                print(f"Health: {health.status}")
                continue
            elif query.lower() == "artifacts":
                if args.provider == "offline":
                    artifacts = loader.list_available_artifacts()
                    for artifact_type, file_paths in artifacts.items():
                        print(f"{artifact_type}: {len(file_paths)} files")
                else:
                    print("Artifact listing only available for offline provider")
                continue
            elif not query:
                continue

            # Run query
            result = provider.generate(prompt=query, session_id=session_id)

            print("\nRESPONSE:")
            print(result.content)

            if args.verbose:
                print(f"\nUsage: {json.dumps(result.usage, indent=2)}")
                print(f"Metadata: {json.dumps(result.metadata, indent=2)}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            if args.verbose:
                import traceback

                traceback.print_exc()

    print("\nGoodbye!")


def print_help():
    """Print help information"""
    print(
        """
Available commands:
  help        - Show this help
  health      - Check provider health
  artifacts   - List available artifacts (offline provider only)
  quit/exit   - Exit interactive mode

Example queries:
  - "Show mirroring ratios for BTC/USD last week"
  - "Which exchange led price moves yesterday?"
  - "Highlight spread floor periods"
  - "Summarize ICP invariance results"
  - "Generate risk assessment summary"
"""
    )


def run_sample_queries(args):
    """Run sample compliance queries"""
    sample_queries = [
        "Show mirroring ratios vs. arbitrage controls for ETH/USD last week.",
        "Which exchange acted as price leader for BTC/USD yesterday, and how persistent was that leadership?",
        "Highlight any periods where spread floors emerged despite high volatility.",
        "Compare lead–lag betas between Binance and Coinbase over the last 24 hours.",
        "Summarize coordination risk bands (LOW/AMBER/RED) across the top 3 venues for BTC/USD in the last week.",
        "List all alternative explanations that could account for the coordination signal flagged on 2025-09-15.",
        "Summarize ICP invariance results by environment for BTC/USD over the last 14 days; include FDR q-values and sample sizes.",
        "Report VMM over-identification p-values and stability for BTC/USD (seed 42), plus moment scaling provenance.",
        "Which alternative explanations (arbitrage latency, fee tiers, inventory shocks) were triggered for ETH/USD in the last 72h?",
        "Generate a screening memo for BTC/USD (past week): headline verdict (LOW/AMBER/RED), top drivers (lead-lag, mirroring, regimes), and caveats.",
    ]

    print(f"Running {len(sample_queries)} sample queries with provider: {args.provider}")
    print("=" * 80)

    # Create provider
    if args.provider == "chatbase":
        provider = create_provider("chatbase")
    else:
        provider = OfflineMockProvider(artifacts_dir=args.artifacts_dir)

    results = []

    for i, query in enumerate(sample_queries, 1):
        print(f"\nQuery {i}: {query}")
        print("-" * 60)

        result = provider.generate(prompt=query, session_id=f"sample_{args.provider}_{i}")

        print(f"Response: {result.content[:200]}...")
        print(f"Intent: {result.usage.get('intent', 'unknown')}")

        results.append(
            {
                "query": query,
                "response": result.content,
                "intent": result.usage.get("intent", "unknown"),
                "session_id": result.session_id,
            }
        )

    # Save results
    output_file = f"sample_queries_{args.provider}_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
