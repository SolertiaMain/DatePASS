from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class InvitationStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"


class InviteCreate(BaseModel):
    recipient_name: str = Field(min_length=1, max_length=80)
    date: datetime
    place: str = Field(min_length=1, max_length=140)
    message: str = Field(default="", max_length=500)

    @field_validator("recipient_name", "place", "message")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("date")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("date must include a timezone offset, for example 2026-06-14T20:00:00-06:00")
        return value


class MemoryCreate(BaseModel):
    partner_name: str = Field(min_length=1, max_length=80)
    date: datetime
    place: str = Field(min_length=1, max_length=140)
    story: str = Field(min_length=1, max_length=600)
    title: str = Field(default="Our First Date", min_length=1, max_length=80)
    memory_number: int = Field(default=1, ge=1, le=999)
    photo_base64: str = Field(
        default="",
        max_length=1_500_000,
        description="Optional PNG/JPEG data URL or base64 image used as the Wallet strip image.",
    )

    @field_validator("partner_name", "place", "story", "title", "photo_base64")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("date")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("date must include a timezone offset, for example 2026-06-23T13:00:00-06:00")
        return value


class InviteResponse(BaseModel):
    id: str
    status: InvitationStatus
    pass_url: str
    accept_url: str
    decline_url: str
    status_url: str


class MemoryResponse(BaseModel):
    id: str
    serial_number: str
    pass_url: str
    status_url: str
    preview_url: str


class RespondBody(BaseModel):
    action: Literal["accept", "decline"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
