#!/usr/bin/env python3
"""
Bootstrap AWS Glue database and external tables for ACD Monitor snapshots.

This script creates:
- Glue database: acd_snapshots
- External table: btc_ticks with partition projection
- Proper schema mapping for S3 Parquet files
"""

import json
import sys
from pathlib import Path

import boto3


def create_glue_database():
    """Create the Glue database."""
    glue = boto3.client("glue")

    database_name = "acd_snapshots"

    try:
        glue.get_database(Name=database_name)
        print(f"✅ Database {database_name} already exists")
        return True
    except glue.exceptions.EntityNotFoundException:
        try:
            glue.create_database(
                DatabaseInput={
                    "Name": database_name,
                    "Description": "ACD Monitor snapshot data warehouse",
                    "LocationUri": "s3://acd-monitor-snapshots/",
                }
            )
            print(f"✅ Created database {database_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to create database: {e}")
            return False


def create_btc_ticks_table():
    """Create the BTC ticks table with partition projection."""
    glue = boto3.client("glue")

    table_name = "btc_ticks"
    database_name = "acd_snapshots"

    # Table schema based on observed Parquet structure
    table_input = {
        "Name": table_name,
        "Description": "BTC-USD tick data with partition projection",
        "StorageDescriptor": {
            "Columns": [
                {
                    "Name": "ts_exchange",
                    "Type": "bigint",
                    "Comment": "Exchange timestamp (nanoseconds)",
                },
                {"Name": "best_bid", "Type": "double", "Comment": "Best bid price"},
                {"Name": "best_ask", "Type": "double", "Comment": "Best ask price"},
                {"Name": "last_px", "Type": "double", "Comment": "Last trade price"},
                {"Name": "bid_sz", "Type": "double", "Comment": "Bid size"},
                {"Name": "ask_sz", "Type": "double", "Comment": "Ask size"},
                {"Name": "trade_sz", "Type": "double", "Comment": "Trade size"},
                {"Name": "mid_px", "Type": "double", "Comment": "Computed mid price"},
            ],
            "Location": "s3://acd-monitor-snapshots/snapshots/BTC-USD/",
            "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
            "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
            "SerdeInfo": {
                "SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
            },
            "Parameters": {"classification": "parquet", "compressionType": "none"},
        },
        "PartitionKeys": [
            {"Name": "date", "Type": "string", "Comment": "Date partition (YYYYMMDD)"},
            {"Name": "window", "Type": "string", "Comment": "Time window (HHMM-HHMM)"},
            {"Name": "venue", "Type": "string", "Comment": "Exchange venue"},
        ],
        "Parameters": {
            "projection.enabled": "true",
            "projection.date.type": "date",
            "projection.date.range": "2024/01/01,NOW",
            "projection.date.format": "yyyyMMdd",
            "projection.date.interval": "1",
            "projection.date.interval.unit": "DAYS",
            "projection.window.type": "enum",
            "projection.window.values": "0000-2359,0000-0015,0015-0030,0030-0045,0045-0100,0100-0115,0115-0130,0130-0145,0145-0200,0200-0215,0215-0230,0230-0245,0245-0300,0300-0315,0315-0330,0330-0345,0345-0400,0400-0415,0415-0430,0430-0445,0445-0500,0500-0515,0515-0530,0530-0545,0545-0600,0600-0615,0615-0630,0630-0645,0645-0700,0700-0715,0715-0730,0730-0745,0745-0800,0800-0815,0815-0830,0830-0845,0845-0900,0900-0915,0915-0930,0930-0945,0945-1000,1000-1015,1015-1030,1030-1045,1045-1100,1100-1115,1115-1130,1130-1145,1145-1200,1200-1215,1215-1230,1230-1245,1245-1300,1300-1315,1315-1330,1330-1345,1345-1400,1400-1415,1415-1430,1430-1445,1445-1500,1500-1515,1515-1530,1530-1545,1545-1600,1600-1615,1615-1630,1630-1645,1645-1700,1700-1715,1715-1730,1730-1745,1745-1800,1800-1815,1815-1830,1830-1845,1845-1900,1900-1915,1915-1930,1930-1945,1945-2000,2000-2015,2015-2030,2030-2045,2045-2100,2100-2115,2115-2130,2130-2145,2145-2200,2200-2215,2215-2230,2230-2245,2245-2300,2300-2315,2315-2330,2330-2345,2345-2359",
            "projection.venue.type": "enum",
            "projection.venue.values": "binance,coinbase,kraken,okx,bybit",
            "storage.location.template": "s3://acd-monitor-snapshots/snapshots/BTC-USD/${date}/${window}/ticks/${venue}/",
        },
    }

    try:
        # Try to get existing table
        glue.get_table(DatabaseName=database_name, Name=table_name)
        print(f"✅ Table {table_name} already exists")

        # Update table
        glue.update_table(DatabaseName=database_name, TableInput=table_input)
        print(f"✅ Updated table {table_name}")
        return True

    except glue.exceptions.EntityNotFoundException:
        try:
            glue.create_table(DatabaseName=database_name, TableInput=table_input)
            print(f"✅ Created table {table_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to create table: {e}")
            return False


def create_athena_workgroup():
    """Create Athena workgroup for analytics."""
    athena = boto3.client("athena")

    workgroup_name = "acd-analytics"

    try:
        athena.get_work_group(WorkGroup=workgroup_name)
        print(f"✅ Workgroup {workgroup_name} already exists")
        return True
    except athena.exceptions.InvalidRequestException:
        try:
            athena.create_work_group(
                Name=workgroup_name,
                Description="ACD Monitor analytics workgroup",
                WorkGroupConfiguration={
                    "ResultConfiguration": {
                        "OutputLocation": "s3://acd-monitor-derived/athena-results/",
                        "EncryptionConfiguration": {"EncryptionOption": "SSE_S3"},
                    },
                    "EnforceWorkGroupConfiguration": True,
                    "PublishCloudWatchMetricsEnabled": True,
                },
            )
            print(f"✅ Created workgroup {workgroup_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to create workgroup: {e}")
            return False


def main():
    """Main function."""
    print("🗄️ Bootstrapping AWS Glue for ACD Monitor...")

    # Create database
    if not create_glue_database():
        sys.exit(1)

    # Create table
    if not create_btc_ticks_table():
        sys.exit(1)

    # Create Athena workgroup
    if not create_athena_workgroup():
        sys.exit(1)

    print("\n✅ Glue bootstrap complete!")
    print("🎯 Database: acd_snapshots")
    print("📊 Table: btc_ticks (with partition projection)")
    print("🔍 Athena workgroup: acd-analytics")

    return True


if __name__ == "__main__":
    main()
