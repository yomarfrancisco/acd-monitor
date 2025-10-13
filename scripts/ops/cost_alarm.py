#!/usr/bin/env python3
"""
Create CloudWatch cost alarm for ACD Monitor.

This script:
- Creates a monthly cost alarm
- Sets up SNS topic for notifications
- Configures alarm thresholds
"""

import boto3
import json
import sys
from pathlib import Path


def create_sns_topic():
    """Create SNS topic for cost alarms."""
    sns = boto3.client("sns")

    topic_name = "acd-cost-alarms"

    try:
        response = sns.create_topic(Name=topic_name)
        topic_arn = response["TopicArn"]
        print(f"✅ Created SNS topic: {topic_arn}")
        return topic_arn
    except Exception as e:
        print(f"❌ Failed to create SNS topic: {e}")
        return None


def create_cost_alarm(topic_arn, threshold=150):
    """Create CloudWatch cost alarm."""
    cloudwatch = boto3.client("cloudwatch")

    alarm_name = "acd-monthly-cost-alarm"

    try:
        cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            ComparisonOperator="GreaterThanThreshold",
            EvaluationPeriods=1,
            MetricName="EstimatedCharges",
            Namespace="AWS/Billing",
            Period=86400,  # 24 hours
            Statistic="Maximum",
            Threshold=threshold,
            ActionsEnabled=True,
            AlarmActions=[topic_arn],
            AlarmDescription=f"ACD Monitor monthly cost alarm (${threshold})",
            Dimensions=[{"Name": "Currency", "Value": "USD"}],
        )
        print(f"✅ Created cost alarm: {alarm_name}")
        return True
    except Exception as e:
        print(f"❌ Failed to create cost alarm: {e}")
        return False


def create_cost_budget(threshold=150):
    """Create AWS Budget for cost tracking."""
    budgets = boto3.client("budgets")

    budget_name = "acd-monthly-budget"

    try:
        budgets.create_budget(
            AccountId=boto3.client("sts").get_caller_identity()["Account"],
            Budget={
                "BudgetName": budget_name,
                "BudgetLimit": {"Amount": str(threshold), "Unit": "USD"},
                "TimeUnit": "MONTHLY",
                "BudgetType": "COST",
                "CostFilters": {"Service": ["Amazon S3", "Amazon Athena", "AWS Glue"]},
            },
            NotificationsWithSubscribers=[
                {
                    "Notification": {
                        "NotificationType": "ACTUAL",
                        "ComparisonOperator": "GREATER_THAN",
                        "Threshold": 80,
                        "ThresholdType": "PERCENTAGE",
                    },
                    "Subscribers": [
                        {
                            "SubscriptionType": "EMAIL",
                            "Address": "admin@example.com",  # Replace with actual email
                        }
                    ],
                }
            ],
        )
        print(f"✅ Created budget: {budget_name}")
        return True
    except Exception as e:
        print(f"❌ Failed to create budget: {e}")
        return False


def generate_setup_docs(topic_arn):
    """Generate setup documentation."""
    docs_path = Path("analysis/infra/COST_ALARM_SETUP.md")
    docs_path.parent.mkdir(parents=True, exist_ok=True)

    with open(docs_path, "w") as f:
        f.write("# Cost Alarm Setup\n\n")
        f.write("## SNS Topic\n\n")
        f.write(f"**Topic ARN**: `{topic_arn}`\n\n")
        f.write("## Email Subscription\n\n")
        f.write("To receive cost alerts, subscribe your email to the SNS topic:\n\n")
        f.write("```bash\n")
        f.write(
            f"aws sns subscribe --topic-arn {topic_arn} --protocol email --notification-endpoint your-email@example.com\n"
        )
        f.write("```\n\n")
        f.write("## CloudWatch Alarm\n\n")
        f.write("- **Name**: `acd-monthly-cost-alarm`\n")
        f.write("- **Threshold**: $150/month\n")
        f.write("- **Metric**: AWS/Billing EstimatedCharges\n")
        f.write("- **Action**: SNS notification\n\n")
        f.write("## AWS Budget\n\n")
        f.write("- **Name**: `acd-monthly-budget`\n")
        f.write("- **Limit**: $150/month\n")
        f.write("- **Services**: S3, Athena, Glue\n")
        f.write("- **Notifications**: 80% threshold\n\n")
        f.write("## Cost Optimization\n\n")
        f.write("### S3 Lifecycle Rules Applied\n")
        f.write("- Snapshots: 45d → IA, 60d → Glacier, 90d → Deep Archive\n")
        f.write("- Derived data: 30d → IA, 180d → Delete\n")
        f.write("- Multipart uploads: 7d cleanup\n\n")
        f.write("### Expected Monthly Costs\n")
        f.write("- **S3 Storage**: ~$5-20 (depending on data volume)\n")
        f.write("- **Athena Queries**: ~$5/TB scanned\n")
        f.write("- **Glue**: ~$0.44/DPU-hour\n")
        f.write("- **Total**: <$50/month for typical usage\n\n")


def main():
    """Main function."""
    print("💰 Setting up cost monitoring for ACD Monitor...")

    # Create SNS topic
    topic_arn = create_sns_topic()
    if not topic_arn:
        sys.exit(1)

    # Create cost alarm
    if not create_cost_alarm(topic_arn):
        sys.exit(1)

    # Create budget
    if not create_cost_budget():
        print("⚠️ Budget creation failed - check permissions")

    # Generate docs
    generate_setup_docs(topic_arn)
    print(f"📋 Setup docs written to: analysis/infra/COST_ALARM_SETUP.md")

    print("\n✅ Cost monitoring setup complete!")
    print("📧 Subscribe to SNS topic to receive alerts")
    print("💰 Monthly threshold: $150")

    return True


if __name__ == "__main__":
    main()
