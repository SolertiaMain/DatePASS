import os
import asyncio
import base64

import pytest

os.environ.setdefault("TABLE_NAME", "test-table")
os.environ.setdefault("BUCKET_NAME", "test-bucket")
os.environ.setdefault("WALLET_SECRET_ARN", "test-secret")
os.environ.setdefault("API_BASE_URL", "https://example.com/prod")
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")

from fastapi import HTTPException

import app.main as main


class FakeRepo:
    def __init__(self):
        self.items = {}

    def create(self, item):
        self.items[item["id"]] = item
        return item

    def get(self, item_id):
        return self.items.get(item_id)


class FakeWallet:
    def __init__(self):
        self.last_pass_payload = None

    def store_memory_photo(self, memory_id, photo, extension, content_type):
        return f"memory-photos/{memory_id}/photo.{extension}"

    def generate_and_store(self, payload):
        self.last_pass_payload = payload
        return f"passes/{payload['id']}/datepass-memory.pkpass"

    def create_photo_url(self, photo_s3_key):
        return f"https://signed.example.com/{photo_s3_key}"


def install_fakes(monkeypatch):
    fake_repo = FakeRepo()
    fake_wallet = FakeWallet()
    monkeypatch.setattr(main, "repo", fake_repo)
    monkeypatch.setattr(main, "wallet", fake_wallet)
    monkeypatch.setattr(main, "get_wallet_secret", lambda: {"creator_api_key": "correct-key"})
    return fake_repo, fake_wallet


def png_file():
    data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )
    return FakeUploadFile("first-date.png", data)


class FakeUploadFile:
    def __init__(self, filename, data):
        self.filename = filename
        self._data = data

    async def read(self, size=-1):
        return self._data[:size] if size >= 0 else self._data


def create_memory_direct(photo):
    return asyncio.run(
        main.create_memory(
            recipient_name="Coco",
            title="Our First Date",
            date="2026-06-23T13:00",
            place="Nolitas, 1pm",
            message="He preparado este recuerdo para recordar nuestra primera cita oficial",
            memory_number=1,
            theme="midnight-romance",
            photo=photo,
        )
    )


def test_admin_form_loads():
    html = main.new_memory_form()
    assert "Create Memory" in html
    assert 'name="photo"' in html


@pytest.mark.parametrize("key", [None, "", "TU_CREATOR_API_KEY_REAL", "wrong-key"])
def test_memory_api_rejects_invalid_key(monkeypatch, key):
    install_fakes(monkeypatch)
    try:
        main.creator_auth(key)
    except HTTPException as exc:
        assert exc.status_code == 401
        assert "Invalid creator key" in exc.detail
        assert "documentation placeholder" in exc.detail
    else:
        raise AssertionError("Expected invalid key")


def test_memory_api_accepts_valid_key(monkeypatch):
    install_fakes(monkeypatch)
    assert main.creator_auth("correct-key") is None


def test_memory_api_requires_photo(monkeypatch):
    install_fakes(monkeypatch)
    try:
        create_memory_direct(None)
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail == "Photo file is required"
    else:
        raise AssertionError("Expected missing photo error")


def test_memory_api_rejects_invalid_photo(monkeypatch):
    install_fakes(monkeypatch)
    try:
        create_memory_direct(FakeUploadFile("photo.txt", b"not-image"))
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail == "Unsupported image format"
    else:
        raise AssertionError("Expected invalid format error")


def test_memory_api_creates_memory_and_returns_pass_url(monkeypatch):
    repo, wallet = install_fakes(monkeypatch)
    payload = create_memory_direct(png_file())
    assert payload["pass_url"].startswith("https://example.com/prod/pass/")
    assert payload["preview_url"].endswith(f"/memories/{payload['id']}/preview")
    assert repo.get(payload["id"])["photo_s3_key"].endswith("/photo.png")
    assert "background.png" in wallet.last_pass_payload["photo_assets"]
    assert "strip.png" in wallet.last_pass_payload["photo_assets"]
    assert "thumbnail.png" in wallet.last_pass_payload["photo_assets"]


def test_memory_preview_loads(monkeypatch):
    repo, _ = install_fakes(monkeypatch)
    repo.create(
        {
            "id": "memory-id",
            "kind": "memory",
            "partner_name": "Coco",
            "memory_date": "2026-06-23T13:00:00-06:00",
            "place": "Nolitas, 1pm",
            "story": "A story",
            "title": "Our First Date",
            "memory_number": 1,
            "photo_s3_key": "memory-photos/memory-id/photo.jpg",
            "pass_s3_key": "passes/memory-id/datepass-memory.pkpass",
            "updated_at": "2026-06-23T19:00:00+00:00",
        }
    )
    body = main.preview_memory("memory-id")
    assert "Our First Date" in body
    assert "/pass/memory-id" in body
