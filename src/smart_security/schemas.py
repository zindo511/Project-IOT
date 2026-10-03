from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SystemMode(StrEnum):
    DISARMED = "DISARMED"
    ARMED = "ARMED"
    PREVIEW = "PREVIEW"
    ENROLLING = "ENROLLING"


class Zone(StrEnum):
    OUTSIDE = "OUTSIDE"
    A = "A"
    B = "B"


class Direction(StrEnum):
    UNKNOWN = "UNKNOWN"
    INCOMING = "INCOMING"
    OUTGOING = "OUTGOING"


class IdentityStatus(StrEnum):
    NOT_EVALUATED = "NOT_EVALUATED"
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    UNCERTAIN = "UNCERTAIN"


class EventLevel(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ALARM = "ALARM"
    FAULT = "FAULT"


class EventReason(StrEnum):
    KNOWN_INCOMING_CONFIRMED = "KNOWN_INCOMING_CONFIRMED"
    UNKNOWN_INCOMING_CONFIRMED = "UNKNOWN_INCOMING_CONFIRMED"
    DIRECTION_UNCLEAR_AT_B = "DIRECTION_UNCLEAR_AT_B"
    FACE_QUALITY_INSUFFICIENT = "FACE_QUALITY_INSUFFICIENT"
    DEVICE_OFFLINE = "DEVICE_OFFLINE"
    VISION_FAILURE = "VISION_FAILURE"
    STORAGE_FAILURE = "STORAGE_FAILURE"


class CommandAction(StrEnum):
    START = "START"
    STOP = "STOP"


class CommandStatus(StrEnum):
    PENDING = "PENDING"
    ACKED = "ACKED"
    REJECTED_EXPIRED = "REJECTED_EXPIRED"
    FAILED = "FAILED"


class Observation(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    frame_id: str = Field(min_length=1, max_length=128)
    captured_at: datetime
    track_id: str = Field(min_length=1, max_length=128)
    zone: Zone
    direction: Direction = Direction.UNKNOWN
    face_quality: float = Field(default=0.0, ge=0.0, le=1.0)
    identity: IdentityStatus = IdentityStatus.NOT_EVALUATED
    person_id: str | None = None
    match_score: float | None = Field(default=None, ge=-1.0, le=1.0)

    @model_validator(mode="after")
    def known_requires_person(self) -> "Observation":
        if self.identity == IdentityStatus.KNOWN and not self.person_id:
            raise ValueError("KNOWN observation requires person_id")
        return self


class EventCreate(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    visit_id: str
    device_id: str
    level: EventLevel
    reason: EventReason
    identity: IdentityStatus
    person_id: str | None = None
    occurred_at: datetime = Field(default_factory=utc_now)
    evidence_path: str | None = None


class Event(EventCreate):
    acknowledged: bool = False


class BuzzerCommand(BaseModel):
    command_id: str = Field(default_factory=lambda: str(uuid4()))
    device_id: str
    action: CommandAction
    duration_ms: int | None = Field(default=None, ge=0)
    expires_at: datetime
    generation: int = Field(ge=1)
    status: CommandStatus = CommandStatus.PENDING


class ModeRequest(BaseModel):
    mode: SystemMode


class AckRequest(BaseModel):
    device_id: str
    status: CommandStatus

