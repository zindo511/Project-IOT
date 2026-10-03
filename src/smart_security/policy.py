from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime

from .config import PolicySettings
from .schemas import (
    Direction,
    EventCreate,
    EventLevel,
    EventReason,
    IdentityStatus,
    Observation,
    Zone,
)


@dataclass
class TrackState:
    zones: deque[Zone]
    votes: deque[IdentityStatus]
    person_votes: deque[str | None]
    last_vote_at: datetime | None = None
    seen_a: int = 0
    seen_b: int = 0
    emitted_reasons: set[EventReason] = field(default_factory=set)


class PolicyEngine:
    """Conservative per-track policy. Missing evidence never produces an alarm."""

    def __init__(self, settings: PolicySettings):
        self.settings = settings
        self.tracks: dict[str, TrackState] = {}

    def reset(self) -> None:
        self.tracks.clear()

    def process(self, observation: Observation) -> EventCreate | None:
        state = self.tracks.setdefault(
            observation.track_id,
            TrackState(
                zones=deque(maxlen=self.settings.vote_window * 2),
                votes=deque(maxlen=self.settings.vote_window),
                person_votes=deque(maxlen=self.settings.vote_window),
            ),
        )
        state.zones.append(observation.zone)
        if observation.zone == Zone.A:
            state.seen_a += 1
        elif observation.zone == Zone.B:
            state.seen_b += 1

        incoming = (
            observation.direction == Direction.INCOMING
            or (state.seen_a >= self.settings.min_zone_observations and state.seen_b >= self.settings.min_zone_observations)
        )

        if observation.zone != Zone.B:
            return None

        if not incoming:
            return self._emit_once(
                state, observation, EventLevel.WARNING,
                EventReason.DIRECTION_UNCLEAR_AT_B, IdentityStatus.UNCERTAIN,
            )

        if observation.identity == IdentityStatus.NOT_EVALUATED:
            return None

        if observation.face_quality < self.settings.min_face_quality:
            observation = observation.model_copy(update={"identity": IdentityStatus.UNCERTAIN, "person_id": None})

        if state.last_vote_at is not None:
            spacing_ms = (observation.captured_at - state.last_vote_at).total_seconds() * 1000
            if spacing_ms < self.settings.min_vote_spacing_ms:
                return None

        state.last_vote_at = observation.captured_at
        state.votes.append(observation.identity)
        state.person_votes.append(observation.person_id)
        counts = Counter(state.votes)

        if counts[IdentityStatus.KNOWN] >= self.settings.required_votes:
            people = Counter(person for person in state.person_votes if person)
            person_id = people.most_common(1)[0][0] if people else observation.person_id
            return self._emit_once(
                state, observation, EventLevel.INFO,
                EventReason.KNOWN_INCOMING_CONFIRMED, IdentityStatus.KNOWN, person_id,
            )

        if counts[IdentityStatus.UNKNOWN] >= self.settings.required_votes:
            return self._emit_once(
                state, observation, EventLevel.ALARM,
                EventReason.UNKNOWN_INCOMING_CONFIRMED, IdentityStatus.UNKNOWN,
            )

        if counts[IdentityStatus.UNCERTAIN] >= self.settings.required_votes:
            return self._emit_once(
                state, observation, EventLevel.WARNING,
                EventReason.FACE_QUALITY_INSUFFICIENT, IdentityStatus.UNCERTAIN,
            )
        return None

    @staticmethod
    def _emit_once(
        state: TrackState,
        observation: Observation,
        level: EventLevel,
        reason: EventReason,
        identity: IdentityStatus,
        person_id: str | None = None,
    ) -> EventCreate | None:
        if reason in state.emitted_reasons:
            return None
        state.emitted_reasons.add(reason)
        return EventCreate(
            visit_id=observation.track_id,
            device_id=observation.device_id,
            level=level,
            reason=reason,
            identity=identity,
            person_id=person_id,
            occurred_at=observation.captured_at,
        )
