from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path
from typing import Any

import boto3
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7

from .config import get_settings, get_wallet_secret

ASSET_DIR = Path(__file__).parent / "assets"
PASS_ASSETS = ["icon.png", "icon@2x.png", "logo.png", "logo@2x.png"]


class WalletPassService:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.s3 = boto3.client("s3", region_name=settings.aws_region)

    def _build_pass_json(self, invitation: dict[str, Any]) -> dict[str, Any]:
        secret = get_wallet_secret()
        invitation_id = invitation["id"]
        status = invitation["status"]
        status_display = {
            "pending": "Waiting for Confirmation",
            "accepted": "Confirmed ❤️",
            "declined": "Declined 💔",
        }[status]
        accept_url = f"{self.settings.api_base_url}/accept/{invitation_id}"
        status_url = f"{self.settings.api_base_url}/status/{invitation_id}"
        decline_url = f"{self.settings.api_base_url}/decline/{invitation_id}"

        return {
            "formatVersion": 1,
            "passTypeIdentifier": secret["pass_type_identifier"],
            "teamIdentifier": secret["team_identifier"],
            "organizationName": secret["organization_name"],
            "serialNumber": invitation_id,
            "description": "DatePass romantic invitation",
            "logoText": "DatePass",
            "backgroundColor": "rgb(19, 22, 31)",
            "foregroundColor": "rgb(255, 255, 255)",
            "labelColor": "rgb(190, 195, 209)",
            "relevantDate": invitation["invitation_date"],
            "barcodes": [
                {
                    "format": "PKBarcodeFormatQR",
                    "message": accept_url,
                    "messageEncoding": "iso-8859-1",
                    "altText": "Scan to respond",
                }
            ],
            "boardingPass": {
                "transitType": "PKTransitTypeGeneric",
                "headerFields": [
                    {"key": "flight", "label": "FLIGHT", "value": "FR-2026"}
                ],
                "primaryFields": [
                    {"key": "origin", "label": "FROM", "value": "Friend Zone"},
                    {"key": "destination", "label": "TO", "value": "Date Zone"},
                ],
                "secondaryFields": [
                    {"key": "passenger", "label": "PASSENGER", "value": invitation["recipient_name"]},
                    {"key": "departure", "label": "DEPARTURE", "value": invitation["invitation_date"], "dateStyle": "PKDateStyleMedium", "timeStyle": "PKDateStyleShort"},
                ],
                "auxiliaryFields": [
                    {"key": "seat", "label": "SEAT", "value": "Next to Franco"},
                    {"key": "status", "label": "STATUS", "value": status_display},
                ],
                "backFields": [
                    {"key": "place", "label": "PLACE", "value": invitation["place"]},
                    {"key": "message", "label": "MESSAGE", "value": invitation.get("message", "") or "A premium invitation, made with code."},
                    {"key": "status_url", "label": "CHECK STATUS", "value": status_url},
                    {"key": "decline_url", "label": "DECLINE INVITATION", "value": decline_url},
                    {"key": "privacy", "label": "PRIVACY", "value": "This pass contains a private invitation. Share it only with its intended passenger."},
                ],
            },
        }

    @staticmethod
    def _sha1(data: bytes) -> str:
        return hashlib.sha1(data, usedforsecurity=False).hexdigest()

    @staticmethod
    def _load_private_key(private_key_pem: str, password: str | None):
        password_bytes = password.encode("utf-8") if password else None
        return serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=password_bytes)

    @staticmethod
    def _sign_manifest(manifest_bytes: bytes) -> bytes:
        secret = get_wallet_secret()
        certificate = x509.load_pem_x509_certificate(secret["certificate_pem"].encode("utf-8"))
        wwdr_certificate = x509.load_pem_x509_certificate(secret["wwdr_certificate_pem"].encode("utf-8"))
        private_key = WalletPassService._load_private_key(secret["private_key_pem"], secret.get("private_key_password"))
        return (
            pkcs7.PKCS7SignatureBuilder()
            .set_data(manifest_bytes)
            .add_signer(certificate, private_key, hashes.SHA256())
            .add_certificate(wwdr_certificate)
            .sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.DetachedSignature, pkcs7.PKCS7Options.Binary])
        )

    def build_pkpass(self, invitation: dict[str, Any]) -> bytes:
        files: dict[str, bytes] = {
            "pass.json": json.dumps(self._build_pass_json(invitation), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        }
        for filename in PASS_ASSETS:
            asset_path = ASSET_DIR / filename
            if not asset_path.exists():
                raise RuntimeError(f"Required pass asset is missing: {asset_path}")
            files[filename] = asset_path.read_bytes()

        manifest = {name: self._sha1(data) for name, data in sorted(files.items())}
        manifest_bytes = json.dumps(manifest, separators=(",", ":"), sort_keys=True).encode("utf-8")
        files["manifest.json"] = manifest_bytes
        files["signature"] = self._sign_manifest(manifest_bytes)

        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        return output.getvalue()

    def generate_and_store(self, invitation: dict[str, Any]) -> str:
        key = f"passes/{invitation['id']}/datepass.pkpass"
        self.s3.put_object(
            Bucket=self.settings.bucket_name,
            Key=key,
            Body=self.build_pkpass(invitation),
            ContentType="application/vnd.apple.pkpass",
            ContentDisposition='attachment; filename="datepass.pkpass"',
            CacheControl="no-store, max-age=0",
            ServerSideEncryption="AES256",
        )
        return key

    def create_download_url(self, pass_s3_key: str) -> str:
        return self.s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.settings.bucket_name,
                "Key": pass_s3_key,
                "ResponseContentType": "application/vnd.apple.pkpass",
                "ResponseContentDisposition": 'attachment; filename="datepass.pkpass"',
            },
            ExpiresIn=self.settings.presigned_url_ttl_seconds,
        )
