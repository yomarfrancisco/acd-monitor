#!/usr/bin/env python3
"""
Setup Athena/Glue for Zero-Copy S3 Queries
===========================================

This script sets up AWS Glue Data Catalog and Athena for zero-copy queries
on the S3 snapshots data, enabling analysis without downloading data locally.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import boto3

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AthenaGlueSetup:
    """Setup Athena/Glue for zero-copy S3 queries."""

    def __init__(self):
        self.glue_client = boto3.client("glue")
        self.athena_client = boto3.client("athena")
        self.s3_client = boto3.client("s3")

        # Configuration
        self.database_name = "acd_snapshots"
        self.table_name = "btc_ticks"
        self.bucket_name = "acd-monitor-snapshots"
        self.s3_prefix = "snapshots/BTC-USD/"

    def create_database(self) -> bool:
        """Create Glue database for ACD snapshots."""
        logger.info(f"Creating Glue database: {self.database_name}")

        try:
            self.glue_client.create_database(
                DatabaseInput={
                    "Name": self.database_name,
                    "Description": "ACD Monitor snapshots database",
                    "LocationUri": f"s3://{self.bucket_name}/{self.s3_prefix}",
                }
            )
            logger.info(f"✅ Database {self.database_name} created successfully")
            return True

        except self.glue_client.exceptions.AlreadyExistsException:
            logger.info(f"✅ Database {self.database_name} already exists")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create database: {e}")
            return False

    def create_table(self) -> bool:
        """Create Glue table for BTC ticks data."""
        logger.info(f"Creating Glue table: {self.table_name}")

        table_input = {
            "Name": self.table_name,
            "Description": "BTC-USD tick data from ACD monitor",
            "TableType": "EXTERNAL_TABLE",
            "Parameters": {"classification": "parquet", "compressionType": "none"},
            "StorageDescriptor": {
                "Columns": [
                    {"Name": "ts_exchange", "Type": "bigint", "Comment": "Exchange timestamp"},
                    {"Name": "best_bid", "Type": "double", "Comment": "Best bid price"},
                    {"Name": "best_ask", "Type": "double", "Comment": "Best ask price"},
                    {"Name": "last_px", "Type": "double", "Comment": "Last trade price"},
                    {"Name": "bid_sz", "Type": "double", "Comment": "Bid size"},
                    {"Name": "ask_sz", "Type": "double", "Comment": "Ask size"},
                    {"Name": "trade_sz", "Type": "double", "Comment": "Trade size"},
                    {"Name": "venue", "Type": "string", "Comment": "Exchange venue"},
                    {"Name": "date", "Type": "string", "Comment": "Date partition"},
                    {"Name": "window", "Type": "string", "Comment": "Time window partition"},
                ],
                "Location": f"s3://{self.bucket_name}/{self.s3_prefix}",
                "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                "SerdeInfo": {
                    "SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
                },
            },
            "PartitionKeys": [
                {"Name": "date", "Type": "string"},
                {"Name": "window", "Type": "string"},
                {"Name": "venue", "Type": "string"},
            ],
        }

        try:
            self.glue_client.create_table(DatabaseName=self.database_name, TableInput=table_input)
            logger.info(f"✅ Table {self.table_name} created successfully")
            return True

        except self.glue_client.exceptions.AlreadyExistsException:
            logger.info(f"✅ Table {self.table_name} already exists")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create table: {e}")
            return False

    def add_partitions(self) -> bool:
        """Add partitions for existing data."""
        logger.info("Adding partitions for existing data...")

        try:
            # List existing partitions
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=self.s3_prefix, Delimiter="/"
            )

            partitions = []
            for prefix in response.get("CommonPrefixes", []):
                path = prefix["Prefix"]
                # Extract date and window from path
                # Format: snapshots/BTC-USD/20250929/1200-1230/ticks/venue/part-0000.parquet
                parts = path.split("/")
                if len(parts) >= 4:
                    date = parts[2]  # 20250929
                    window = parts[3]  # 1200-1230
                    venue = parts[5] if len(parts) > 5 else "unknown"

                    partitions.append(
                        {
                            "Values": [date, window, venue],
                            "StorageDescriptor": {
                                "Location": f"s3://{self.bucket_name}/{path}",
                                "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                                "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                                "SerdeInfo": {
                                    "SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
                                },
                            },
                        }
                    )

            if partitions:
                # Add partitions in batches
                batch_size = 25  # Glue limit
                for i in range(0, len(partitions), batch_size):
                    batch = partitions[i : i + batch_size]
                    self.glue_client.batch_create_partition(
                        DatabaseName=self.database_name,
                        TableName=self.table_name,
                        PartitionInputList=batch,
                    )
                    logger.info(
                        f"✅ Added {len(partitions)} partitions (batch {i//batch_size + 1})"
                    )

                logger.info(f"✅ Added {len(partitions)} partitions successfully")
                return True
            else:
                logger.warning("No partitions found to add")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to add partitions: {e}")
            return False

    def create_workgroup(self) -> bool:
        """Create Athena workgroup for ACD analysis."""
        logger.info("Creating Athena workgroup...")

        workgroup_config = {
            "ResultConfiguration": {
                "OutputLocation": f"s3://{self.bucket_name}/athena-results/",
                "EncryptionConfiguration": {"EncryptionOption": "SSE_S3"},
            },
            "EnforceWorkGroupConfiguration": True,
            "PublishCloudWatchMetricsEnabled": True,
        }

        try:
            self.athena_client.create_work_group(
                Name="acd-analytics",
                Description="ACD Monitor analytics workgroup",
                WorkGroupConfiguration=workgroup_config,
            )
            logger.info("✅ Athena workgroup 'acd-analytics' created successfully")
            return True

        except self.athena_client.exceptions.InvalidRequestException as e:
            if "already exists" in str(e):
                logger.info("✅ Athena workgroup 'acd-analytics' already exists")
                return True
            else:
                logger.error(f"❌ Failed to create workgroup: {e}")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to create workgroup: {e}")
            return False

    def test_query(self) -> bool:
        """Test Athena query functionality."""
        logger.info("Testing Athena query functionality...")

        test_query = f"""
        SELECT 
            date,
            window,
            venue,
            COUNT(*) as record_count,
            MIN(ts_exchange) as min_timestamp,
            MAX(ts_exchange) as max_timestamp
        FROM {self.database_name}.{self.table_name}
        WHERE date >= '20250928'
        GROUP BY date, window, venue
        ORDER BY date, window, venue
        LIMIT 10
        """

        try:
            response = self.athena_client.start_query_execution(
                QueryString=test_query,
                WorkGroup="acd-analytics",
                ResultConfiguration={
                    "OutputLocation": f"s3://{self.bucket_name}/athena-results/test/"
                },
            )

            query_id = response["QueryExecutionId"]
            logger.info(f"✅ Test query started: {query_id}")

            # Wait for completion
            import time

            while True:
                status = self.athena_client.get_query_execution(QueryExecutionId=query_id)
                state = status["QueryExecution"]["Status"]["State"]

                if state in ["SUCCEEDED"]:
                    logger.info("✅ Test query completed successfully")
                    return True
                elif state in ["FAILED", "CANCELLED"]:
                    logger.error(f"❌ Test query failed: {status['QueryExecution']['Status']}")
                    return False
                else:
                    logger.info(f"⏳ Query status: {state}")
                    time.sleep(5)

        except Exception as e:
            logger.error(f"❌ Failed to test query: {e}")
            return False

    def run_setup(self) -> bool:
        """Run complete Athena/Glue setup."""
        logger.info("Starting Athena/Glue setup for zero-copy S3 queries...")

        steps = [
            ("Create database", self.create_database),
            ("Create table", self.create_table),
            ("Add partitions", self.add_partitions),
            ("Create workgroup", self.create_workgroup),
            ("Test query", self.test_query),
        ]

        for step_name, step_func in steps:
            logger.info(f"🔄 {step_name}...")
            if not step_func():
                logger.error(f"❌ Setup failed at step: {step_name}")
                return False

        logger.info("✅ Athena/Glue setup completed successfully!")
        return True


def main():
    """Main execution function."""
    setup = AthenaGlueSetup()
    success = setup.run_setup()

    if success:
        print("\n🎉 Athena/Glue setup complete!")
        print("✅ Zero-copy S3 queries are now available")
        print("✅ Ready for real data analysis")
    else:
        print("\n❌ Athena/Glue setup failed")
        print("❌ Check logs for details")


if __name__ == "__main__":
    main()
