#!/usr/bin/env python3
"""
Fix the S3 statement in an IAM policy to add the bucket ARN for s3:ListBucket.
ListBucket requires the bucket ARN (arn:aws:s3:::bucket-name), not the object ARN (bucket-name/*).

# Fix noma_tt_policy (bucket name inferred from current policy)
python dev/launcher/scripts/fix_s3_listbucket_policy.py <policy_name>

# Specify bucket explicitly
python dev/launcher/scripts/fix_s3_listbucket_policy.py <policy_name> -b <bucket_name>

# With profile
python dev/launcher/scripts/fix_s3_listbucket_policy.py <policy_name> -p my-admin-profile
"""

import argparse
import json
import re
import boto3


S3_ACTIONS = {"s3:PutObject", "s3:GetObject", "s3:DeleteObject", "s3:ListBucket"}


def extract_bucket_from_resource(resource: str | list) -> str | None:
    """Extract bucket name from S3 resource ARN(s)."""
    if isinstance(resource, str):
        resources = [resource]
    else:
        resources = resource
    for r in resources:
        if not isinstance(r, str):
            continue
        m = re.match(r"arn:aws:s3:::([^/]+)(?:/\*)?", r)
        if m:
            return m.group(1)
    return None


def fix_s3_listbucket_policy(
    policy_name: str,
    bucket_name: str | None = None,
    profile: str | None = None,
    region: str = "us-east-1",
) -> bool:
    """
    Update the policy's S3 statement to include bucket ARN for ListBucket.
    Returns True if the policy was updated, False if no change needed.
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    iam = session.client("iam")
    sts = session.client("sts")
    account_id = sts.get_caller_identity()["Account"]
    policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"

    try:
        iam.get_policy(PolicyArn=policy_arn)
    except iam.exceptions.NoSuchEntityException:
        print(f"Policy '{policy_name}' not found.")
        return False

    policy_versions = iam.list_policy_versions(PolicyArn=policy_arn)
    current = next((v for v in policy_versions["Versions"] if v["IsDefaultVersion"]), None)
    if not current:
        print("Could not find default policy version.")
        return False

    current_doc = iam.get_policy_version(
        PolicyArn=policy_arn, VersionId=current["VersionId"]
    )["PolicyVersion"]["Document"]

    new_statements = []
    updated = False

    for stmt in current_doc.get("Statement", []):
        actions = stmt.get("Action")
        if isinstance(actions, str):
            actions = [actions]
        if not actions:
            new_statements.append(stmt)
            continue

        has_s3 = any(a in S3_ACTIONS for a in actions)
        if not has_s3:
            new_statements.append(stmt)
            continue

        resource = stmt.get("Resource")
        if isinstance(resource, str):
            resource_list = [resource]
        else:
            resource_list = list(resource) if resource else []

        bucket = bucket_name or extract_bucket_from_resource(resource_list)
        if not bucket:
            print("Could not determine bucket name. Pass --bucket explicitly.")
            new_statements.append(stmt)
            continue

        bucket_arn = f"arn:aws:s3:::{bucket}"
        objects_arn = f"arn:aws:s3:::{bucket}/*"

        if bucket_arn in resource_list and objects_arn in resource_list:
            print(f"S3 statement already has both bucket and objects ARNs. No change needed.")
            new_statements.append(stmt)
            continue

        new_resource = [bucket_arn, objects_arn]
        new_stmt = {**stmt, "Resource": new_resource}
        new_statements.append(new_stmt)
        updated = True
        print(f"Updated S3 statement: Resource now includes {bucket_arn} and {objects_arn}")

    if not updated:
        return False

    new_doc = {**current_doc, "Statement": new_statements}

    try:
        iam.create_policy_version(
            PolicyArn=policy_arn,
            PolicyDocument=json.dumps(new_doc),
            SetAsDefault=True,
        )
    except iam.exceptions.LimitExceededException:
        non_default = [v for v in policy_versions["Versions"] if not v["IsDefaultVersion"]]
        non_default.sort(key=lambda v: v["CreateDate"])
        if not non_default:
            raise RuntimeError(
                f"Policy '{policy_name}' has 5 versions. Delete an old version in IAM console first."
            )
        iam.delete_policy_version(PolicyArn=policy_arn, VersionId=non_default[0]["VersionId"])
        print("Deleted oldest policy version to make room.")
        iam.create_policy_version(
            PolicyArn=policy_arn,
            PolicyDocument=json.dumps(new_doc),
            SetAsDefault=True,
        )

    print(f"Policy '{policy_name}' updated successfully.")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Fix S3 ListBucket resource in an IAM policy (add bucket ARN)."
    )
    parser.add_argument(
        "policy_name",
        help="IAM policy name (e.g. noma_tt_policy)",
    )
    parser.add_argument(
        "-b", "--bucket",
        default=None,
        help="S3 bucket name (optional; extracted from policy if not provided)",
    )
    parser.add_argument("-p", "--profile", default=None, help="AWS profile")
    parser.add_argument("-r", "--region", default="us-east-1", help="AWS region")
    args = parser.parse_args()

    fix_s3_listbucket_policy(
        args.policy_name,
        bucket_name=args.bucket,
        profile=args.profile,
        region=args.region,
    )


if __name__ == "__main__":
    main()
