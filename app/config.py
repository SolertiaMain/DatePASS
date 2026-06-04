from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache

import boto3


@dataclass(frozen=True)
class Settings:
    table_name: str
    bucket_name: str
    wallet_secret_arn: str
    api_base_url: str
    presigned_url_ttl_seconds: int
    aws_region: str
    cors_allow_origins: list[str]
    event_bus_name: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        table_name=os.environ["TABLE_NAME"],
        bucket_name=os.environ["BUCKET_NAME"],
        wallet_secret_arn=os.environ["WALLET_SECRET_ARN"],
        api_base_url=os.environ["API_BASE_URL"].rstrip("/"),
        presigned_url_ttl_seconds=int(os.getenv("PRESIGNED_URL_TTL_SECONDS", "900")),
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        cors_allow_origins=[origin.strip() for origin in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if origin.strip()],
        event_bus_name=os.getenv("EVENT_BUS_NAME", ""),
    )


@lru_cache(maxsize=1)
def get_wallet_secret() -> dict[str, str]:
    settings = get_settings()
    client = boto3.client("secretsmanager", region_name=settings.aws_region)
    response = client.get_secret_value(SecretId=settings.wallet_secret_arn)
    payload = response.get("SecretString")
    if not payload:
        raise RuntimeError("Wallet secret must be stored as SecretString JSON")
    secret = json.loads(payload)
    required = {
        "pass_type_identifier",
        "team_identifier",
        "organization_name",
        "certificate_pem",
        "private_key_pem",
        "wwdr_certificate_pem",
        "creator_api_key",
    }
    missing = sorted(required.difference(secret))
    if missing:
        raise RuntimeError(f"Wallet secret is missing fields: {', '.join(missing)}")
    return secret
