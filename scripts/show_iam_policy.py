#!/usr/bin/env python3
"""
Show the policy document for a given IAM policy by name.
Supports both customer-managed and AWS managed policies.
"""

import argparse
import json
import boto3


def show_iam_policy(policy_name: str, profile: str | None = None, region: str = "us-east-1") -> None:
    session = boto3.Session(profile_name=profile, region_name=region)
    iam = session.client("iam")
    sts = session.client("sts")
    account_id = sts.get_caller_identity()["Account"]

    # Try customer-managed first, then AWS managed
    arns_to_try = [
        f"arn:aws:iam::{account_id}:policy/{policy_name}",
        f"arn:aws:iam::aws:policy/{policy_name}",
    ]

    policy_arn = None
    policy = None
    for arn in arns_to_try:
        try:
            policy = iam.get_policy(PolicyArn=arn)["Policy"]
            policy_arn = arn
            break
        except iam.exceptions.NoSuchEntityException:
            continue

    if not policy:
        print(f"Policy '{policy_name}' not found (tried customer and AWS managed).")
        return

    version_id = policy["DefaultVersionId"]
    version = iam.get_policy_version(PolicyArn=policy_arn, VersionId=version_id)
    document = version["PolicyVersion"]["Document"]

    print("=" * 60)
    print(f"IAM Policy: {policy_name}")
    print("=" * 60)
    print(f"ARN:        {policy_arn}")
    print(f"Version:    {version_id}")
    print(f"Created:    {policy['CreateDate']}")
    print()
    print("--- Policy Document ---")
    print(json.dumps(document, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Show IAM policy document by policy name")
    parser.add_argument("policy_name", help="IAM policy name (e.g. noma_tt_policy or AmazonS3ReadOnlyAccess)")
    parser.add_argument("-p", "--profile", default=None, help="AWS profile (default: default)")
    parser.add_argument("-r", "--region", default="us-east-1", help="AWS region")
    args = parser.parse_args()

    show_iam_policy(args.policy_name, profile=args.profile, region=args.region)


if __name__ == "__main__":
    main()
