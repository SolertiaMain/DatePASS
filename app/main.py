from __future__ import annotations

import hmac
import json
import logging
import uuid
from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

import boto3

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from mangum import Mangum

from .config import get_settings, get_wallet_secret
from .models import InviteCreate, InviteResponse, InvitationStatus, MemoryResponse, utc_now_iso
from .photos import PHOTO_MAX_BYTES, build_wallet_photo_assets, validate_photo
from .repository import InvitationRepository
from .templates import admin_memory_form, memory_preview, page
from .wallet_pass import WalletPassService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("datepass")

settings = get_settings()

app = FastAPI(title="DatePass", version="1.0.0", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-DatePass-Creator-Key"],
)

repo = InvitationRepository()
wallet = WalletPassService()


def creator_auth(x_datepass_creator_key: Annotated[str | None, Header()] = None) -> None:
    expected = get_wallet_secret()["creator_api_key"]
    if not x_datepass_creator_key or not hmac.compare_digest(x_datepass_creator_key, expected):
        raise HTTPException(status_code=401, detail="Invalid creator key. Verify that X-DatePass-Creator-Key contains the real key, not a documentation placeholder.")


def require_invitation(invitation_id: str):
    invitation = repo.get(invitation_id)
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return invitation


def urls(invitation_id: str) -> dict[str, str]:
    return {
        "pass_url": f"{settings.api_base_url}/pass/{invitation_id}",
        "accept_url": f"{settings.api_base_url}/accept/{invitation_id}",
        "decline_url": f"{settings.api_base_url}/decline/{invitation_id}",
        "status_url": f"{settings.api_base_url}/status/{invitation_id}",
    }


def memory_urls(memory_id: str) -> dict[str, str]:
    return {
        "pass_url": f"{settings.api_base_url}/pass/{memory_id}",
        "status_url": f"{settings.api_base_url}/status/{memory_id}",
        "preview_url": f"{settings.api_base_url}/memories/{memory_id}/preview",
    }


def parse_memory_date(value: str) -> str:
    raw_value = value.strip()
    if not raw_value:
        raise HTTPException(status_code=422, detail="Date is required")
    normalized = raw_value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid date") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("America/Monterrey"))
    return parsed.isoformat()


def publish_response_event(invitation: dict) -> None:
    if not settings.event_bus_name:
        return
    try:
        client = boto3.client("events", region_name=settings.aws_region)
        client.put_events(Entries=[{
            "Source": "datepass.invitation",
            "DetailType": "InvitationResponded",
            "Detail": json.dumps({
                "id": invitation["id"],
                "recipient_name": invitation["recipient_name"],
                "status": invitation["status"],
                "updated_at": invitation["updated_at"],
            }),
            "EventBusName": settings.event_bus_name,
        }])
    except Exception:
        logger.exception("Unable to publish response event", extra={"invitation_id": invitation["id"]})


@app.get("/health")
def health():
    return {"ok": True, "service": "datepass"}


@app.post("/invite", response_model=InviteResponse, dependencies=[Depends(creator_auth)])
def create_invite(payload: InviteCreate):
    invitation_id = str(uuid.uuid4())
    now = utc_now_iso()
    invitation = {
        "id": invitation_id,
        "recipient_name": payload.recipient_name,
        "invitation_date": payload.date.isoformat(),
        "place": payload.place,
        "message": payload.message,
        "status": InvitationStatus.pending.value,
        "pass_s3_key": "",
        "created_at": now,
        "updated_at": now,
        "accepted_at": "",
        "declined_at": "",
    }
    repo.create(invitation)
    pass_key = wallet.generate_and_store(invitation)
    repo.set_pass_key(invitation_id, pass_key)
    logger.info("Invitation created", extra={"invitation_id": invitation_id})
    return {"id": invitation_id, "status": invitation["status"], **urls(invitation_id)}


@app.get("/admin/memories/new", response_class=HTMLResponse)
def new_memory_form():
    return admin_memory_form()


@app.post("/memories", response_model=MemoryResponse, dependencies=[Depends(creator_auth)])
async def create_memory(
    recipient_name: Annotated[str, Form(..., min_length=1, max_length=80)],
    title: Annotated[str, Form(..., min_length=1, max_length=80)],
    date: Annotated[str, Form(...)],
    place: Annotated[str, Form(..., min_length=1, max_length=140)],
    message: Annotated[str, Form(..., min_length=1, max_length=600)],
    memory_number: Annotated[int, Form(..., ge=1, le=999)],
    theme: Annotated[str, Form()] = "midnight-romance",
    photo: Annotated[UploadFile | None, File()] = None,
):
    if photo is None:
        raise HTTPException(status_code=422, detail="Photo file is required")
    photo_data = await photo.read(PHOTO_MAX_BYTES + 1)
    try:
        validated_photo = validate_photo(photo_data, photo.filename)
        wallet_photo_assets = build_wallet_photo_assets(validated_photo.data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    memory_id = str(uuid.uuid4())
    now = utc_now_iso()
    memory = {
        "id": memory_id,
        "kind": "memory",
        "partner_name": recipient_name.strip(),
        "memory_date": parse_memory_date(date),
        "place": place.strip(),
        "story": message.strip(),
        "title": title.strip(),
        "memory_number": memory_number,
        "theme": theme.strip() or "midnight-romance",
        "status": "saved",
        "pass_s3_key": "",
        "photo_s3_key": "",
        "photo_content_type": validated_photo.content_type,
        "photo_filename": validated_photo.filename,
        "created_at": now,
        "updated_at": now,
    }
    memory_for_pass = {**memory, "photo_assets": wallet_photo_assets}
    try:
        photo_key = wallet.store_memory_photo(memory_id, validated_photo.data, validated_photo.extension, validated_photo.content_type)
        pass_key = wallet.generate_and_store(memory_for_pass)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    memory["photo_s3_key"] = photo_key
    memory["pass_s3_key"] = pass_key
    repo.create(memory)
    logger.info("Memory created", extra={"memory_id": memory_id})
    return {"id": memory_id, "serial_number": memory_id, **memory_urls(memory_id)}


@app.get("/pass/{invitation_id}")
def get_pass(invitation_id: str):
    invitation = require_invitation(invitation_id)
    return RedirectResponse(wallet.create_download_url(invitation["pass_s3_key"]), status_code=302)


@app.get("/memories/{memory_id}/preview", response_class=HTMLResponse)
def preview_memory(memory_id: str):
    memory = require_invitation(memory_id)
    if memory.get("kind") != "memory":
        raise HTTPException(status_code=404, detail="Memory not found")
    if not memory.get("photo_s3_key"):
        raise HTTPException(status_code=404, detail="Memory photo not found")
    pass_url = memory_urls(memory_id)["pass_url"]
    photo_url = wallet.create_photo_url(memory["photo_s3_key"])
    return memory_preview(memory, photo_url, pass_url)


@app.get("/accept/{invitation_id}", response_class=HTMLResponse)
def accept_page(invitation_id: str):
    invitation = require_invitation(invitation_id)
    if invitation["status"] == InvitationStatus.accepted.value:
        return page("Confirmed", "Already confirmed ❤️", "Your seat next to Franco is reserved.", link_url=urls(invitation_id)["pass_url"], link_label="Download refreshed Wallet pass")
    return page("Accept invitation", "Ready to enter the Date Zone?", "Tap below to confirm the invitation. Wallet will receive a freshly generated pass the next time it is downloaded.", invitation_id, "accept")


@app.get("/decline/{invitation_id}", response_class=HTMLResponse)
def decline_page(invitation_id: str):
    invitation = require_invitation(invitation_id)
    if invitation["status"] == InvitationStatus.declined.value:
        return page("Declined", "Invitation declined 💔", "The invitation has already been marked as declined.", link_url=urls(invitation_id)["pass_url"], link_label="Download updated Wallet pass")
    return page("Decline invitation", "Decline this DatePass?", "Tap below only when you are sure. The pass status will be regenerated.", invitation_id, "decline")


@app.post("/api/respond/{invitation_id}", response_class=HTMLResponse)
def respond(invitation_id: str, action: Annotated[str, Form()]):
    if action not in {"accept", "decline"}:
        raise HTTPException(status_code=422, detail="Invalid action")
    status = InvitationStatus.accepted if action == "accept" else InvitationStatus.declined
    invitation = repo.respond(invitation_id, status)
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    pass_key = wallet.generate_and_store(invitation)
    repo.set_pass_key(invitation_id, pass_key)
    publish_response_event(invitation)
    logger.info("Invitation response recorded", extra={"invitation_id": invitation_id, "status": status.value})
    if status == InvitationStatus.accepted:
        return page("Confirmed", "Confirmed ❤️", "Your seat next to Franco is officially reserved.", link_url=urls(invitation_id)["pass_url"], link_label="Download refreshed Wallet pass")
    return page("Declined", "Declined 💔", "The invitation has been marked as declined.", link_url=urls(invitation_id)["pass_url"], link_label="Download updated Wallet pass")


def status_payload(invitation: dict) -> dict:
    invitation_id = invitation["id"]
    if invitation.get("kind") == "memory":
        return {
            "id": invitation_id,
            "kind": "memory",
            "partner_name": invitation["partner_name"],
            "date": invitation["memory_date"],
            "place": invitation["place"],
            "title": invitation["title"],
            "memory_number": invitation["memory_number"],
            "theme": invitation.get("theme", "midnight-romance"),
            "serial_number": invitation_id,
            "pass_url": memory_urls(invitation_id)["pass_url"],
            "preview_url": memory_urls(invitation_id)["preview_url"],
            "updated_at": invitation["updated_at"],
        }
    return {
        "id": invitation_id,
        "recipient_name": invitation["recipient_name"],
        "date": invitation["invitation_date"],
        "place": invitation["place"],
        "status": invitation["status"],
        "pass_url": urls(invitation_id)["pass_url"],
        "updated_at": invitation["updated_at"],
    }


@app.get("/status/{invitation_id}")
def get_status(invitation_id: str, request: Request):
    invitation = require_invitation(invitation_id)
    payload = status_payload(invitation)
    if "text/html" in request.headers.get("accept", ""):
        if invitation.get("kind") == "memory":
            return HTMLResponse(page("Memory status", invitation["title"], f"Franco + {invitation['partner_name']} · Place: {invitation['place']}", link_url=payload["pass_url"], link_label="Download Wallet memory"))
        state = {"pending": "Waiting for confirmation ✨", "accepted": "Confirmed ❤️", "declined": "Declined 💔"}[invitation["status"]]
        return HTMLResponse(page("Invitation status", state, f"Passenger: {invitation['recipient_name']} · Destination: Date Zone · Place: {invitation['place']}", link_url=payload["pass_url"], link_label="Download Wallet pass"))
    return payload


@app.get("/api/status/{invitation_id}")
def get_status_json(invitation_id: str):
    return status_payload(require_invitation(invitation_id))


handler = Mangum(app, lifespan="off")
