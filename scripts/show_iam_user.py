#!/usr/bin/env python3
"""
Show IAM details for a given AWS IAM user.
Run with an administrator profile to view user permissions, groups, and policies.
"""

import argparse
import json
import boto3


def show_iam_user(user_name: str, profile: str | None = None, region: str = "us-east-1") -> None:
    session = boto3.Session(profile_name=profile, region_name=region)
    iam = session.client("iam")

    try:
        user = iam.get_user(UserName=user_name)["User"]
    except iam.exceptions.NoSuchEntityException:
        print(f"User '{user_name}' not found.")
        return

    print("=" * 60)
    print(f"IAM User: {user_name}")
    print("=" * 60)
    print(f"ARN:         {user['Arn']}")
    print(f"Created:     {user['CreateDate']}")
    print(f"Path:       {user.get('Path', '/')}")
    print()

    # Attached managed policies
    print("--- Attached Managed Policies ---")
    paginator = iam.get_paginator("list_attached_user_policies")
    for page in paginator.paginate(UserName=user_name):
        for policy in page.get("AttachedPolicies", []):
            print(f"  • {policy['PolicyName']} ({policy['PolicyArn']})")
    print()

    # Inline policies
    print("--- Inline Policies ---")
    paginator = iam.get_paginator("list_user_policies")
    for page in paginator.paginate(UserName=user_name):
        for policy_name in page.get("PolicyNames", []):
            doc = iam.get_user_policy(UserName=user_name, PolicyName=policy_name)
            print(f"  • {policy_name}")
            print(f"    {json.dumps(doc['PolicyDocument'], indent=4)}")
    print()

    # Groups
    print("--- Groups ---")
    for group in iam.list_groups_for_user(UserName=user_name).get("Groups", []):
        print(f"  • {group['GroupName']} ({group['Arn']})")
        for page in iam.get_paginator("list_attached_group_policies").paginate(GroupName=group["GroupName"]):
            for policy in page.get("AttachedPolicies", []):
                print(f"      └─ {policy['PolicyName']}")
    print()

    # Access keys (metadata only, no secrets)
    print("--- Access Keys ---")
    for key in iam.list_access_keys(UserName=user_name).get("AccessKeyMetadata", []):
        status = key["Status"]
        created = key["CreateDate"].strftime("%Y-%m-%d")
        print(f"  • {key['AccessKeyId']}  Status: {status}  Created: {created}")


def main():
    parser = argparse.ArgumentParser(description="Show IAM details for an AWS user")
    parser.add_argument("user_name", help="IAM user name to inspect")
    parser.add_argument("-p", "--profile", default=None, help="AWS profile (default: default)")
    parser.add_argument("-r", "--region", default="us-east-1", help="AWS region")
    args = parser.parse_args()

    show_iam_user(args.user_name, profile=args.profile, region=args.region)


if __name__ == "__main__":
    main()
