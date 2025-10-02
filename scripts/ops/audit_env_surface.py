#!/usr/bin/env python3
"""
AWS Environment Surface Audit
Check for presence/absence of AWS credentials without printing values.
"""

import os
import json
from pathlib import Path

def audit_env_surface():
    """Audit AWS environment surface without exposing secrets."""
    audit_results = {
        "timestamp": "2025-09-30T18:30:00Z",
        "environment_sources": {},
        "aws_credentials_present": {},
        "summary": {}
    }
    
    # Check environment variables
    env_vars = [
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY', 
        'AWS_SESSION_TOKEN',
        'AWS_REGION',
        'AWS_DEFAULT_REGION',
        'S3_BUCKET',
        'SNAPSHOTS_BUCKET'
    ]
    
    env_present = {}
    for var in env_vars:
        env_present[var] = var in os.environ
    
    audit_results["environment_sources"]["env_vars"] = env_present
    
    # Check AWS credentials file
    aws_creds_path = Path.home() / '.aws' / 'credentials'
    aws_config_path = Path.home() / '.aws' / 'config'
    
    audit_results["environment_sources"]["aws_files"] = {
        "credentials_file_exists": aws_creds_path.exists(),
        "config_file_exists": aws_config_path.exists(),
        "credentials_path": str(aws_creds_path),
        "config_path": str(aws_config_path)
    }
    
    # Check for AWS profile environment variable
    audit_results["environment_sources"]["aws_profile"] = {
        "AWS_PROFILE_set": "AWS_PROFILE" in os.environ,
        "AWS_DEFAULT_PROFILE_set": "AWS_DEFAULT_PROFILE" in os.environ
    }
    
    # Check for boto3 session configuration
    try:
        import boto3
        session = boto3.Session()
        audit_results["environment_sources"]["boto3_session"] = {
            "region_name": session.region_name,
            "profile_name": session.profile_name,
            "available_profiles": session.available_profiles if hasattr(session, 'available_profiles') else []
        }
    except ImportError:
        audit_results["environment_sources"]["boto3_session"] = {
            "error": "boto3 not available"
        }
    
    # Check for GitHub Actions environment indicators
    github_actions = {
        "GITHUB_ACTIONS": os.getenv("GITHUB_ACTIONS"),
        "GITHUB_WORKFLOW": os.getenv("GITHUB_WORKFLOW"),
        "GITHUB_RUN_ID": os.getenv("GITHUB_RUN_ID")
    }
    
    audit_results["environment_sources"]["github_actions"] = github_actions
    
    # Check for Vercel environment indicators
    vercel_env = {
        "VERCEL": os.getenv("VERCEL"),
        "VERCEL_ENV": os.getenv("VERCEL_ENV"),
        "VERCEL_REGION": os.getenv("VERCEL_REGION")
    }
    
    audit_results["environment_sources"]["vercel"] = vercel_env
    
    # Summary of credential sources
    credential_sources = []
    
    if any(env_present[var] for var in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']):
        credential_sources.append("environment_variables")
    
    if audit_results["environment_sources"]["aws_files"]["credentials_file_exists"]:
        credential_sources.append("aws_credentials_file")
    
    if audit_results["environment_sources"]["boto3_session"].get("profile_name"):
        credential_sources.append("aws_profile")
    
    audit_results["summary"] = {
        "credential_sources": credential_sources,
        "primary_context": "github_actions" if github_actions["GITHUB_ACTIONS"] else "vercel" if vercel_env["VERCEL"] else "local",
        "aws_region": os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "not_set"))
    }
    
    return audit_results

if __name__ == "__main__":
    results = audit_env_surface()
    print(json.dumps(results, indent=2))
