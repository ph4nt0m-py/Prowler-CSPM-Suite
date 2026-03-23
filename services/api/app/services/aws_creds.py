"""Resolve AWS environment variables for Prowler from decrypted credential payloads."""

from __future__ import annotations

from typing import Any

import boto3
from botocore.exceptions import ClientError

from app.models.credential import CredentialAuthMethod
from app.security.crypto import AwsAssumeRolePayload, AwsStaticKeysPayload, decrypt_json_payload


def resolve_aws_env_for_credential(
    ciphertext: bytes,
    auth_method: CredentialAuthMethod,
) -> dict[str, str]:
    data = decrypt_json_payload(ciphertext)
    if auth_method == CredentialAuthMethod.static_keys:
        p = AwsStaticKeysPayload.model_validate(data)
        env = {
            "AWS_ACCESS_KEY_ID": p.access_key_id,
            "AWS_SECRET_ACCESS_KEY": p.secret_access_key,
        }
        if p.session_token:
            env["AWS_SESSION_TOKEN"] = p.session_token
        return env
    if auth_method == CredentialAuthMethod.assume_role:
        p = AwsAssumeRolePayload.model_validate(data)
        base = p.base
        sts = boto3.client(
            "sts",
            aws_access_key_id=base.access_key_id,
            aws_secret_access_key=base.secret_access_key,
            aws_session_token=base.session_token or None,
        )
        kwargs: dict[str, Any] = {"RoleArn": p.role_arn, "RoleSessionName": "cloudaudit-prowler"}
        if p.external_id:
            kwargs["ExternalId"] = p.external_id
        try:
            assumed = sts.assume_role(**kwargs)
        except ClientError as e:
            raise ValueError(f"sts:AssumeRole failed: {e}") from e
        creds = assumed["Credentials"]
        return {
            "AWS_ACCESS_KEY_ID": creds["AccessKeyId"],
            "AWS_SECRET_ACCESS_KEY": creds["SecretAccessKey"],
            "AWS_SESSION_TOKEN": creds["SessionToken"],
        }
    raise ValueError("Unsupported auth method")


def test_aws_credential(ciphertext: bytes, auth_method: CredentialAuthMethod) -> dict[str, str]:
    env = resolve_aws_env_for_credential(ciphertext, auth_method)
    sts = boto3.client(
        "sts",
        aws_access_key_id=env["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=env["AWS_SECRET_ACCESS_KEY"],
        aws_session_token=env.get("AWS_SESSION_TOKEN"),
    )
    ident = sts.get_caller_identity()
    return {"account": ident.get("Account", ""), "arn": ident.get("Arn", "")}
