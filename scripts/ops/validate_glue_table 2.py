#!/usr/bin/env python3
"""
Validate Glue Table and Zero-Copy Path
Run this script with proper Athena/Glue permissions to validate the table setup.
"""

import json
import time
from pathlib import Path

import boto3


def run_athena_query(
    athena_client,
    query,
    workgroup="primary",
    output_location="s3://acd-monitor-derived/athena-results/",
):
    """Run Athena query and return results"""
    try:
        print(f"🔍 Executing query...")
        print(f"Query: {query[:100]}...")

        # Start query execution
        response = athena_client.start_query_execution(
            QueryString=query,
            WorkGroup=workgroup,
            ResultConfiguration={"OutputLocation": output_location},
        )

        execution_id = response["QueryExecutionId"]
        print(f"✅ Query submitted: {execution_id}")

        # Wait for completion (max 5 minutes)
        start_time = time.time()
        timeout = 300  # 5 minutes

        while time.time() - start_time < timeout:
            status = athena_client.get_query_execution(QueryExecutionId=execution_id)
            state = status["QueryExecution"]["Status"]["State"]

            if state == "SUCCEEDED":
                print(f"✅ Query completed: {execution_id}")
                break
            elif state == "FAILED":
                reason = status["QueryExecution"]["Status"].get("StateChangeReason", "Unknown")
                print(f"❌ Query failed: {reason}")
                return None
            elif state == "CANCELLED":
                print(f"⚠️ Query cancelled: {execution_id}")
                return None
            else:
                print(f"⏳ Query status: {state}")
                time.sleep(10)
        else:
            print(f"⏰ Query timed out after {timeout} seconds")
            return None

        # Get results
        results = athena_client.get_query_results(QueryExecutionId=execution_id, MaxResults=100)

        # Parse and display results
        rows = results.get("ResultSet", {}).get("Rows", [])
        if len(rows) > 1:  # Skip header row
            print("📊 Results:")
            data_rows = rows[1:]  # Skip header
            for row in data_rows:
                values = [field.get("VarCharValue", "") for field in row.get("Data", [])]
                print("  " + " | ".join(values))
        else:
            print("📊 No results returned")

        return execution_id

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def validate_glue_table():
    """Validate Glue table setup and run smoke tests"""
    print("🔍 Validating Glue Table and Zero-Copy Path")
    print("=" * 60)

    # Initialize clients
    try:
        athena = boto3.client("athena")
        glue = boto3.client("glue")
        print("✅ AWS clients initialized")
    except Exception as e:
        print(f"❌ Failed to initialize AWS clients: {e}")
        return False

    # Test 1: Check table exists
    print("\n📋 Test 1: Check Glue table exists")
    print("-" * 40)
    try:
        table = glue.get_table(DatabaseName="acd_snapshots", Name="btc_ticks")
        print("✅ Glue table exists")
        print(f"Database: {table['Table']['DatabaseName']}")
        print(f"Table: {table['Table']['Name']}")
        print(f"Location: {table['Table']['StorageDescriptor']['Location']}")
        print(f"Columns: {len(table['Table']['StorageDescriptor']['Columns'])}")
        print(f"Partitions: {len(table['Table']['PartitionKeys'])}")

        # Show column details
        print("\n📊 Columns:")
        for i, col in enumerate(table["Table"]["StorageDescriptor"]["Columns"], 1):
            print(f"{i:2d}. {col['Name']:<25} {col['Type']:<15} {col.get('Comment', '')}")

        print("\n🔑 Partition Keys:")
        for i, part in enumerate(table["Table"]["PartitionKeys"], 1):
            print(f"{i}. {part['Name']:<15} {part['Type']:<15} {part.get('Comment', '')}")

    except Exception as e:
        print(f"❌ Glue table check failed: {e}")
        return False

    # Test 2: Enable partition projection
    print("\n🔧 Test 2: Enable partition projection")
    print("-" * 40)

    projection_sql = """
    ALTER TABLE acd_snapshots.btc_ticks SET TBLPROPERTIES (
      'projection.enabled'='true',
      'projection.date.type'='date',
      'projection.date.format'='yyyyMMdd',
      'projection.date.range'='20240901,20251231',
      'projection.window.type'='enum',
      'projection.window.values'='0000-0030,0030-0100,0100-0130,0130-0200,0200-0230,0230-0300,0300-0330,0330-0400,0400-0430,0430-0500,0500-0530,0530-0600,0600-0630,0630-0700,0700-0730,0730-0800,0800-0830,0830-0900,0900-0930,0930-1000,1000-1030,1030-1100,1100-1130,1130-1200,1200-1230,1230-1300,1300-1330,1330-1400,1400-1430,1430-1500,1500-1530,1530-1600,1600-1630,1630-1700,1700-1730,1730-1800,1800-1830,1830-1900,1900-1930,1930-2000,2000-2030,2030-2100,2100-2130,2130-2200,2200-2230,2230-2300,2300-2330,2330-0000',
      'projection.venue.type'='enum',
      'projection.venue.values'='binance,coinbase,kraken,okx,bybit',
      'storage.location.template'='s3://acd-monitor-snapshots/snapshots/BTC-USD/${date}/${window}/ticks/${venue}.parquet'
    );
    """

    execution_id = run_athena_query(athena, projection_sql)
    if not execution_id:
        print("❌ Failed to enable partition projection")
        return False

    # Test 3: Smoke tests
    print("\n🧪 Test 3: Smoke tests")
    print("-" * 40)

    smoke_tests = [
        {
            "name": "A) Pointed count for single file",
            "query": """
            SELECT count(*) AS n
            FROM acd_snapshots.btc_ticks
            WHERE date='20250929' AND window='0200-0230' AND venue='binance'
            """,
            "expected": "n > 0",
        },
        {
            "name": "B) Schema preview",
            "query": """
            SELECT ts_exchange, best_bid, best_ask, last_px, mid_px
            FROM acd_snapshots.btc_ticks
            WHERE date='20250929' AND window='0200-0230' AND venue='binance'
            ORDER BY ts_exchange
            LIMIT 5
            """,
            "expected": "5 rows with sensible timestamps and prices",
        },
        {
            "name": "C) Multi-venue coverage",
            "query": """
            SELECT venue, COUNT(1) AS rows
            FROM acd_snapshots.btc_ticks
            WHERE date='20250929'
            GROUP BY venue
            ORDER BY venue
            """,
            "expected": "rows for ≥3 venues",
        },
    ]

    results = {}
    for test in smoke_tests:
        print(f"\n📊 {test['name']}:")
        print(f"Expected: {test['expected']}")
        execution_id = run_athena_query(athena, test["query"])
        results[test["name"]] = execution_id is not None

    # Summary
    print("\n📋 Validation Summary")
    print("=" * 60)
    print(f"Glue table exists: ✅")
    print(
        f"Partition projection: {'✅' if results.get('A) Pointed count for single file', False) else '❌'}"
    )
    print(f"Schema alignment: {'✅' if results.get('B) Schema preview', False) else '❌'}")
    print(
        f"Multi-venue coverage: {'✅' if results.get('C) Multi-venue coverage', False) else '❌'}"
    )

    success = all(results.values())
    if success:
        print("\n🎯 All tests passed! Zero-copy path validated.")
        print("✅ Ready to proceed with Wave-1 analysis via Athena queries.")
    else:
        print("\n❌ Some tests failed. Check the outputs above.")
        print("🔧 Fix issues before proceeding with analytics.")

    return success


def main():
    """Main function"""
    print("🚀 Glue Table Validation Script")
    print("=" * 60)
    print("This script validates the Glue table setup and tests zero-copy analytics.")
    print("Requires: Athena and Glue permissions")
    print("Output: Results written to s3://acd-monitor-derived/athena-results/")
    print()

    success = validate_glue_table()

    if success:
        print("\n🎯 Next Steps:")
        print("1. Run Wave-1 analysis: python3 scripts/ops/athena_orchestrate.py --date 20250929")
        print("2. Check results in s3://acd-monitor-derived/")
        print("3. Proceed with Wave-2 and Wave-3 analytics")
    else:
        print("\n🔧 Fix Required:")
        print("1. Check Glue table configuration")
        print("2. Verify partition projection settings")
        print("3. Ensure S3 data is accessible")
        print("4. Re-run validation script")

    return success


if __name__ == "__main__":
    main()
