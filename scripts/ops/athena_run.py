#!/usr/bin/env python3
"""
Execute Athena queries and generate analytics reports.

This script:
- Executes SQL queries from sql/athena/
- Polls for completion
- Generates summary reports
- Writes results to analysis/infra/athena/
"""

import boto3
import json
import time
import sys
from pathlib import Path
from datetime import datetime


def execute_query(query_sql, workgroup="acd-analytics"):
    """Execute an Athena query and return execution ID."""
    athena = boto3.client("athena")

    try:
        response = athena.start_query_execution(
            QueryString=query_sql,
            WorkGroup=workgroup,
            ResultConfiguration={"OutputLocation": "s3://acd-monitor-derived/athena-results/"},
        )
        execution_id = response["QueryExecutionId"]
        print(f"🚀 Started query execution: {execution_id}")
        return execution_id
    except Exception as e:
        print(f"❌ Failed to start query: {e}")
        return None


def wait_for_completion(execution_id, max_wait=300):
    """Wait for query completion."""
    athena = boto3.client("athena")

    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            response = athena.get_query_execution(QueryExecutionId=execution_id)
            status = response["QueryExecution"]["Status"]["State"]

            if status == "SUCCEEDED":
                print(f"✅ Query completed successfully: {execution_id}")
                return True
            elif status == "FAILED":
                reason = response["QueryExecution"]["Status"].get(
                    "StateChangeReason", "Unknown error"
                )
                print(f"❌ Query failed: {reason}")
                return False
            elif status == "CANCELLED":
                print(f"⚠️ Query was cancelled: {execution_id}")
                return False
            else:
                print(f"⏳ Query {status}... waiting")
                time.sleep(10)

        except Exception as e:
            print(f"❌ Error checking query status: {e}")
            return False

    print(f"⏰ Query timed out after {max_wait} seconds")
    return False


def get_query_results(execution_id):
    """Get query results."""
    athena = boto3.client("athena")

    try:
        # Get result location
        response = athena.get_query_execution(QueryExecutionId=execution_id)
        result_location = response["QueryExecution"]["ResultConfiguration"]["OutputLocation"]

        # Get result metadata
        results_response = athena.get_query_results(QueryExecutionId=execution_id, MaxResults=1000)

        return {
            "result_location": result_location,
            "row_count": len(results_response["ResultSet"]["Rows"]),
            "columns": [
                col["Name"]
                for col in results_response["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]
            ],
            "sample_rows": results_response["ResultSet"]["Rows"][:5],  # First 5 rows
        }
    except Exception as e:
        print(f"❌ Failed to get results: {e}")
        return None


def run_sql_file(sql_file_path):
    """Run a SQL file and return results."""
    sql_path = Path(sql_file_path)

    if not sql_path.exists():
        print(f"❌ SQL file not found: {sql_file_path}")
        return None

    print(f"📄 Running SQL file: {sql_path.name}")

    # Read SQL content
    with open(sql_path) as f:
        query_sql = f.read()

    # Execute query
    execution_id = execute_query(query_sql)
    if not execution_id:
        return None

    # Wait for completion
    if not wait_for_completion(execution_id):
        return None

    # Get results
    results = get_query_results(execution_id)
    if results:
        results["sql_file"] = sql_path.name
        results["execution_id"] = execution_id

    return results


def generate_summary_report(results_list):
    """Generate a summary report."""
    report_path = Path("analysis/infra/athena/ATHENA_PROOF.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w") as f:
        f.write("# Athena Analytics Proof\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")

        f.write("## Query Results Summary\n\n")

        for results in results_list:
            if results:
                f.write(f"### {results['sql_file']}\n")
                f.write(f"- **Execution ID**: {results['execution_id']}\n")
                f.write(f"- **Result Location**: {results['result_location']}\n")
                f.write(f"- **Row Count**: {results['row_count']}\n")
                f.write(f"- **Columns**: {', '.join(results['columns'])}\n\n")

                if results["sample_rows"]:
                    f.write("**Sample Results**:\n")
                    for row in results["sample_rows"]:
                        f.write(f"- {[col.get('VarCharValue', '') for col in row['Data']]}\n")
                f.write("\n")

        f.write("## Cost Analysis\n\n")
        f.write("- **Data Scanned**: Check Athena console for exact bytes\n")
        f.write("- **Query Cost**: Based on data scanned (typically $5/TB)\n")
        f.write("- **Storage Cost**: S3 storage for results\n\n")

        f.write("## Next Steps\n\n")
        f.write("1. Verify query results in S3 output location\n")
        f.write("2. Check Athena console for detailed cost breakdown\n")
        f.write("3. Enable CTAS queries for derived data generation\n")


def main():
    """Main function."""
    print("🔍 Running Athena analytics queries...")

    # Define SQL files to run
    sql_files = [
        "sql/athena/counts_by_date.sql",
        "sql/athena/venue_coverage.sql",
        # Note: mid_ohlc_5s.sql disabled for initial read-only test
    ]

    results_list = []

    for sql_file in sql_files:
        results = run_sql_file(sql_file)
        results_list.append(results)

        if results:
            print(f"✅ {sql_file} completed successfully")
        else:
            print(f"❌ {sql_file} failed")

    # Generate summary report
    generate_summary_report(results_list)
    print(f"📊 Summary report written to: analysis/infra/athena/ATHENA_PROOF.md")

    # Check if all queries succeeded
    successful_queries = sum(1 for r in results_list if r is not None)
    total_queries = len(results_list)

    if successful_queries == total_queries:
        print(f"✅ All {total_queries} queries completed successfully!")
        return True
    else:
        print(f"⚠️ {successful_queries}/{total_queries} queries succeeded")
        return False


if __name__ == "__main__":
    main()
