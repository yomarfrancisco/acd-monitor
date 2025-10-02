#!/usr/bin/env python3
"""
Create/update AWS OIDC role for GitHub Actions CI.

This script creates the minimal IAM role and policy needed for GitHub Actions
to access S3 snapshots and run Athena queries without long-lived credentials.
"""

import json
import boto3
import sys
from pathlib import Path

def get_account_id():
    """Get AWS account ID."""
    sts = boto3.client('sts')
    return sts.get_caller_identity()['Account']

def create_oidc_provider():
    """Create GitHub OIDC provider if it doesn't exist."""
    iam = boto3.client('iam')
    account_id = get_account_id()
    
    try:
        iam.get_open_id_connect_provider(
            OpenIDConnectProviderArn=f"arn:aws:iam::{account_id}:oidc-provider/token.actions.githubusercontent.com"
        )
        print("✅ GitHub OIDC provider already exists")
        return True
    except iam.exceptions.NoSuchEntityException:
        try:
            iam.create_open_id_connect_provider(
                Url='https://token.actions.githubusercontent.com',
                ThumbprintList=['6938fd4d98bab03faadb97b34396831e3780aea1'],
                ClientIDList=['sts.amazonaws.com']
            )
            print("✅ Created GitHub OIDC provider")
            return True
        except Exception as e:
            print(f"❌ Failed to create OIDC provider: {e}")
            return False

def create_ci_role():
    """Create the CI OIDC role."""
    iam = boto3.client('iam')
    account_id = get_account_id()
    
    # Load trust policy
    trust_policy_path = Path(__file__).parent.parent.parent / 'infra/iam/ci_oidc_role.json'
    with open(trust_policy_path) as f:
        trust_policy = json.load(f)
    
    # Replace placeholder with actual account ID
    trust_policy_str = json.dumps(trust_policy).replace('ACCOUNT_ID', account_id)
    
    role_name = 'acd-ci-oidc'
    role_arn = f'arn:aws:iam::{account_id}:role/{role_name}'
    
    try:
        # Try to get existing role
        iam.get_role(RoleName=role_name)
        print(f"✅ Role {role_name} already exists")
        
        # Update trust policy
        iam.update_assume_role_policy(
            RoleName=role_name,
            PolicyDocument=trust_policy_str
        )
        print(f"✅ Updated trust policy for role {role_name}")
        
    except iam.exceptions.NoSuchEntityException:
        # Create new role
        iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=trust_policy_str,
            Description='GitHub Actions OIDC role for ACD Monitor CI',
            MaxSessionDuration=3600
        )
        print(f"✅ Created role {role_name}")
    
    return role_arn

def create_ci_policy():
    """Create the CI policy."""
    iam = boto3.client('iam')
    account_id = get_account_id()
    
    # Load policy document
    policy_path = Path(__file__).parent.parent.parent / 'infra/iam/ci_oidc_policy.json'
    with open(policy_path) as f:
        policy_doc = json.load(f)
    
    policy_name = 'acd-ci-oidc-policy'
    policy_arn = f'arn:aws:iam::{account_id}:policy/{policy_name}'
    
    try:
        # Try to get existing policy
        iam.get_policy(PolicyArn=policy_arn)
        print(f"✅ Policy {policy_name} already exists")
        
        # Create new version
        response = iam.create_policy_version(
            PolicyArn=policy_arn,
            PolicyDocument=json.dumps(policy_doc),
            SetAsDefault=True
        )
        print(f"✅ Updated policy {policy_name}")
        
    except iam.exceptions.NoSuchEntityException:
        # Create new policy
        iam.create_policy(
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_doc),
            Description='Minimal permissions for ACD Monitor CI OIDC role'
        )
        print(f"✅ Created policy {policy_name}")
    
    return policy_arn

def attach_policy_to_role():
    """Attach policy to role."""
    iam = boto3.client('iam')
    account_id = get_account_id()
    
    role_name = 'acd-ci-oidc'
    policy_arn = f'arn:aws:iam::{account_id}:policy/acd-ci-oidc-policy'
    
    try:
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn=policy_arn
        )
        print(f"✅ Attached policy to role {role_name}")
        return True
    except Exception as e:
        print(f"❌ Failed to attach policy: {e}")
        return False

def main():
    """Main function."""
    print("🔧 Setting up AWS OIDC role for GitHub Actions CI...")
    
    # Create OIDC provider
    if not create_oidc_provider():
        sys.exit(1)
    
    # Create role
    role_arn = create_ci_role()
    print(f"📋 Role ARN: {role_arn}")
    
    # Create policy
    policy_arn = create_ci_policy()
    print(f"📋 Policy ARN: {policy_arn}")
    
    # Attach policy to role
    if not attach_policy_to_role():
        sys.exit(1)
    
    print("\n✅ OIDC role setup complete!")
    print(f"🎯 Use this role ARN in GitHub Actions: {role_arn}")
    
    return True

if __name__ == "__main__":
    main()
