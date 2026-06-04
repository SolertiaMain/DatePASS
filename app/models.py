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


class InviteResponse(BaseModel):
    id: str
    status: InvitationStatus
    pass_url: str
    accept_url: str
    decline_url: str
    status_url: str


class RespondBody(BaseModel):
    action: Literal["accept", "decline"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
