#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the JSON payload for AWS Secrets Manager")
    parser.add_argument("--pass-type-id", required=True)
    parser.add_argument("--team-id", required=True)
    parser.add_argument("--organization", default="DatePass")
    parser.add_argument("--certificate", required=True, help="Pass Type ID certificate in PEM format")
    parser.add_argument("--private-key", required=True, help="Private key in PEM format")
    parser.add_argument("--wwdr-certificate", required=True, help="Apple WWDR certificate in PEM format")
    parser.add_argument("--private-key-password", default="")
    parser.add_argument("--creator-api-key", required=True)
    args = parser.parse_args()
    print(json.dumps({
        "pass_type_identifier": args.pass_type_id,
        "team_identifier": args.team_id,
        "organization_name": args.organization,
        "certificate_pem": read(args.certificate),
        "private_key_pem": read(args.private_key),
        "private_key_password": args.private_key_password,
        "wwdr_certificate_pem": read(args.wwdr_certificate),
        "creator_api_key": args.creator_api_key,
    }, indent=2))


if __name__ == "__main__":
    main()
