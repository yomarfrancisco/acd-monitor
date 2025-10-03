#!/usr/bin/env python3
"""
Check the results of the 7-day backfill.
"""

import json

import boto3


def check_results():
    """Check the results of the 7-day backfill."""
    s3_client = boto3.client("s3")
    bucket = "acd-monitor-snapshots"

    print("🔍 CHECKING 7-DAY BACKFILL RESULTS")
    print("=" * 80)

    # Check run log
    try:
        response = s3_client.get_object(Bucket=bucket, Key="analysis/coinapi_1s/run_log.json")
        run_log = json.loads(response["Body"].read().decode("utf-8"))

        print(f"📊 RUN SUMMARY:")
        print(f"   Successes: {run_log['successes']}")
        print(f"   Failures: {run_log['failures']}")
        print(f"   Panel Status: {run_log['panel_status']}")

        print(f"\n📊 VENUE SUMMARY:")
        for venue, venue_data in run_log["venues"].items():
            successes = sum(
                1 for day_data in venue_data["days"].values() if day_data["status"] == "success"
            )
            failures = sum(
                1 for day_data in venue_data["days"].values() if day_data["status"] == "failed"
            )
            print(f"   {venue}: {successes} successes, {failures} failures")

    except Exception as e:
        print(f"❌ Error reading run log: {e}")

    # Check panel manifest
    try:
        response = s3_client.get_object(
            Bucket=bucket, Key="analysis/coinapi_1s/panel/panel_manifest.json"
        )
        panel_manifest = json.loads(response["Body"].read().decode("utf-8"))

        print(f"\n📊 PANEL SUMMARY:")
        print(f"   Rows: {panel_manifest['n_rows']:,}")
        print(f"   Overall Coverage: {panel_manifest['overall_overlap']:.1f}%")
        print(f"   Start: {panel_manifest['start_time']}")
        print(f"   End: {panel_manifest['end_time']}")

        print(f"\n📊 DAILY COVERAGE:")
        for date, day_data in panel_manifest["daily_overlaps"].items():
            print(
                f"   {date}: {day_data['n_rows']:,} rows, {day_data['coverage_pct']:.1f}% coverage"
            )

    except Exception as e:
        print(f"❌ Error reading panel manifest: {e}")

    # Check analytics summary
    try:
        response = s3_client.get_object(
            Bucket=bucket, Key="analysis/coinapi_1s/summary/summary_1s.json"
        )
        analytics = json.loads(response["Body"].read().decode("utf-8"))

        print(f"\n📊 ANALYTICS SUMMARY:")
        print(f"   Panel Rows: {analytics['panel_stats']['n_rows']:,}")
        print(f"   Duration: {analytics['panel_stats']['duration_hours']:.1f} hours")

        if "spread_stats" in analytics:
            print(f"\n📊 SPREAD STATISTICS:")
            print(f"   Mean Spread: {analytics['spread_stats']['mean_spread_pct']:.3f}%")
            print(f"   Median Spread: {analytics['spread_stats']['median_spread_pct']:.3f}%")
            print(f"   P95 Spread: {analytics['spread_stats']['p95_spread_pct']:.3f}%")

        if "correlations" in analytics:
            print(f"\n📊 CROSS-VENUE CORRELATIONS:")
            for venue1, venue_corrs in analytics["correlations"].items():
                for venue2, corr in venue_corrs.items():
                    if venue1 != venue2:
                        print(f"   {venue1} vs {venue2}: {corr:.4f}")

        if "lead_lag" in analytics:
            print(f"\n📊 LEAD-LAG ANALYSIS:")
            for pair, stats in analytics["lead_lag"].items():
                print(
                    f"   {pair}: Max correlation {stats['max_correlation']:.4f} at lag {stats['best_lag']}"
                )

    except Exception as e:
        print(f"❌ Error reading analytics: {e}")


if __name__ == "__main__":
    check_results()
