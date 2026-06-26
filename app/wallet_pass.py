from __future__ import annotations

import base64
import binascii
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
        if invitation.get("kind") == "memory":
            return self._build_memory_pass_json(invitation)

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

    def _build_memory_pass_json(self, memory: dict[str, Any]) -> dict[str, Any]:
        secret = get_wallet_secret()
        memory_id = memory["id"]
        memory_number = int(memory.get("memory_number") or 1)
        title = memory.get("title") or "Our First Date"
        memory_date = memory["memory_date"]

        pass_json = {
            "formatVersion": 1,
            "passTypeIdentifier": secret["pass_type_identifier"],
            "teamIdentifier": secret["team_identifier"],
            "organizationName": secret["organization_name"],
            "serialNumber": memory_id,
            "description": "DatePass Memories commemorative date pass",
            "logoText": "DATEPASS MEMORIES",
            "backgroundColor": "rgb(48, 31, 76)",
            "foregroundColor": "rgb(255, 255, 255)",
            "labelColor": "rgb(230, 202, 255)",
            "relevantDate": memory_date,
            "eventTicket": {
                "headerFields": [
                    {"key": "memory_no", "label": "MEMORY", "value": f"#{memory_number:03d}"}
                ],
                "primaryFields": [
                    {"key": "title", "label": "DATEPASS MEMORIES", "value": title.upper()}
                ],
                "secondaryFields": [
                    {"key": "couple", "label": "FOR", "value": f"Franco + {memory['partner_name']}"},
                    {
                        "key": "date",
                        "label": "DATE",
                        "value": memory_date,
                        "dateStyle": "PKDateStyleMedium",
                        "timeStyle": "PKDateStyleShort",
                    },
                ],
                "auxiliaryFields": [
                    {"key": "place", "label": "PLACE", "value": memory["place"]}
                ],
                "backFields": [
                    {"key": "place_back", "label": "PLACE", "value": memory["place"]},
                    {"key": "story", "label": "OUR STORY", "value": memory["story"]},
                    {"key": "serial", "label": "SERIAL NUMBER", "value": memory_id},
                    {
                        "key": "note",
                        "label": "DATEPASS MEMORIES",
                        "value": "A private commemorative pass saved as an Apple Wallet memory.",
                    },
                ],
            },
        }
        if memory.get("show_barcode"):
            pass_json["barcodes"] = [
                {
                    "format": "PKBarcodeFormatQR",
                    "message": f"{self.settings.api_base_url}/status/{memory_id}",
                    "messageEncoding": "iso-8859-1",
                    "altText": f"Memory #{memory_number:03d}",
                }
            ]
        return pass_json

    @staticmethod
    def _decode_photo(photo_base64: str) -> bytes:
        if not photo_base64:
            return b""
        _, _, payload = photo_base64.partition(",")
        encoded = payload if payload else photo_base64
        try:
            return base64.b64decode(encoded, validate=True)
        except binascii.Error as exc:
            raise ValueError("photo_base64 must be valid base64") from exc

    @staticmethod
    def _photo_filename(photo: bytes) -> str:
        if photo.startswith(b"\x89PNG\r\n\x1a\n"):
            return "strip.png"
        if photo.startswith(b"\xff\xd8\xff"):
            return "strip.jpg"
        raise ValueError("photo_base64 must be a PNG or JPEG image")

    @staticmethod
    def _pass_photo_assets(invitation: dict[str, Any]) -> dict[str, bytes]:
        photo_assets = invitation.get("photo_assets")
        if photo_assets:
            return photo_assets
        decoded = WalletPassService._decode_photo(invitation.get("photo_base64", ""))
        if decoded:
            return {WalletPassService._photo_filename(decoded): decoded}
        return {}

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
        files.update(self._pass_photo_assets(invitation))
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
        filename = "datepass-memory.pkpass" if invitation.get("kind") == "memory" else "datepass.pkpass"
        key = f"passes/{invitation['id']}/{filename}"
        self.s3.put_object(
            Bucket=self.settings.bucket_name,
            Key=key,
            Body=self.build_pkpass(invitation),
            ContentType="application/vnd.apple.pkpass",
            ContentDisposition=f'attachment; filename="{filename}"',
            CacheControl="no-store, max-age=0",
            ServerSideEncryption="AES256",
        )
        return key

    def store_memory_photo(self, memory_id: str, photo: bytes, extension: str, content_type: str) -> str:
        key = f"memory-photos/{memory_id}/photo.{extension}"
        self.s3.put_object(
            Bucket=self.settings.bucket_name,
            Key=key,
            Body=photo,
            ContentType=content_type,
            CacheControl="private, max-age=3600",
            ServerSideEncryption="AES256",
        )
        return key

    def create_download_url(self, pass_s3_key: str) -> str:
        filename = pass_s3_key.rsplit("/", 1)[-1]
        return self.s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.settings.bucket_name,
                "Key": pass_s3_key,
                "ResponseContentType": "application/vnd.apple.pkpass",
                "ResponseContentDisposition": f'attachment; filename="{filename}"',
            },
            ExpiresIn=self.settings.presigned_url_ttl_seconds,
        )

    def create_photo_url(self, photo_s3_key: str) -> str:
        return self.s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.settings.bucket_name,
                "Key": photo_s3_key,
            },
            ExpiresIn=self.settings.presigned_url_ttl_seconds,
        )
