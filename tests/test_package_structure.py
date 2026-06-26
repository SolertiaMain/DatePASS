from pathlib import Path
from types import SimpleNamespace
import zipfile

from app.wallet_pass import WalletPassService


def test_required_assets_exist():
    root = Path(__file__).parents[1]
    for name in ["icon.png", "icon@2x.png", "logo.png", "logo@2x.png"]:
        assert (root / "app" / "assets" / name).exists()


def test_memory_pass_uses_event_ticket(monkeypatch):
    monkeypatch.setattr(
        "app.wallet_pass.get_wallet_secret",
        lambda: {
            "pass_type_identifier": "pass.com.franco.datepass",
            "team_identifier": "LY46NBJ9S4",
            "organization_name": "DatePass",
        },
    )
    service = object.__new__(WalletPassService)
    service.settings = SimpleNamespace(api_base_url="https://example.com")

    pass_json = service._build_pass_json(
        {
            "id": "memory-uuid",
            "kind": "memory",
            "partner_name": "Coco",
            "memory_date": "2026-06-23T13:00:00-06:00",
            "place": "Nolitas, 1pm",
            "story": "He preparado este recuerdo para recordar nuestra primera cita oficial",
            "title": "Our First Date",
            "memory_number": 1,
        }
    )

    assert pass_json["serialNumber"] == "memory-uuid"
    assert pass_json["description"] == "DatePass Memories commemorative date pass"
    assert "eventTicket" in pass_json
    assert "boardingPass" not in pass_json
    assert "barcodes" not in pass_json
    assert pass_json["backgroundColor"] == "rgb(48, 31, 76)"
    assert pass_json["eventTicket"]["headerFields"][0]["value"] == "#001"
    assert pass_json["eventTicket"]["secondaryFields"][0]["value"] == "Franco + Coco"
    assert pass_json["eventTicket"]["backFields"][1]["label"] == "OUR STORY"


def test_memory_pkpass_includes_uploaded_photo(monkeypatch):
    monkeypatch.setattr(
        "app.wallet_pass.get_wallet_secret",
        lambda: {
            "pass_type_identifier": "pass.com.franco.datepass",
            "team_identifier": "LY46NBJ9S4",
            "organization_name": "DatePass",
        },
    )
    monkeypatch.setattr(WalletPassService, "_sign_manifest", staticmethod(lambda manifest: b"pkcs7-signature"))
    service = object.__new__(WalletPassService)
    service.settings = SimpleNamespace(api_base_url="https://example.com")

    bundle = service.build_pkpass(
        {
            "id": "memory-uuid",
            "kind": "memory",
            "partner_name": "Coco",
            "memory_date": "2026-06-23T13:00:00-06:00",
            "place": "Nolitas, 1pm",
            "story": "He preparado este recuerdo para recordar nuestra primera cita oficial",
            "title": "Our First Date",
            "memory_number": 1,
            "photo_assets": {
                "background.png": b"background",
                "background@2x.png": b"background-2x",
                "background@3x.png": b"background-3x",
                "strip.png": b"strip",
                "strip@2x.png": b"strip-2x",
                "strip@3x.png": b"strip-3x",
                "thumbnail.png": b"thumbnail",
                "thumbnail@2x.png": b"thumbnail-2x",
                "thumbnail@3x.png": b"thumbnail-3x",
            },
        }
    )

    pkpass_path = Path("/tmp/test-memory.pkpass")
    pkpass_path.write_bytes(bundle)
    with zipfile.ZipFile(pkpass_path) as archive:
        assert "background.png" in archive.namelist()
        assert "background@2x.png" in archive.namelist()
        assert "background@3x.png" in archive.namelist()
        assert "strip.png" in archive.namelist()
        assert "strip@2x.png" in archive.namelist()
        assert "strip@3x.png" in archive.namelist()
        assert "thumbnail.png" in archive.namelist()
        assert "thumbnail@2x.png" in archive.namelist()
        assert "thumbnail@3x.png" in archive.namelist()
        assert "manifest.json" in archive.namelist()
        assert "signature" in archive.namelist()
