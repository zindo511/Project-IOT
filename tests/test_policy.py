from datetime import datetime, timedelta, timezone

from smart_security.config import PolicySettings
from smart_security.policy import PolicyEngine
from smart_security.schemas import Direction, EventLevel, IdentityStatus, Observation, Zone


SETTINGS = PolicySettings(
    vote_window=5, required_votes=3, min_zone_observations=2,
    min_vote_spacing_ms=250, min_face_quality=0.65,
    track_timeout_seconds=3.0, device_cooldown_seconds=10.0,
)


def observation(index: int, zone: Zone, identity: IdentityStatus, direction: Direction = Direction.UNKNOWN, track: str = "t1") -> Observation:
    return Observation(
        device_id="door-01", frame_id=str(index),
        captured_at=datetime(2026, 10, 3, tzinfo=timezone.utc) + timedelta(milliseconds=300 * index),
        track_id=track, zone=zone, direction=direction,
        face_quality=0.9 if identity != IdentityStatus.NOT_EVALUATED else 0,
        identity=identity,
        person_id="person-1" if identity == IdentityStatus.KNOWN else None,
        match_score=0.8 if identity == IdentityStatus.KNOWN else None,
    )


def enter_a(engine: PolicyEngine) -> None:
    assert engine.process(observation(0, Zone.A, IdentityStatus.NOT_EVALUATED)) is None
    assert engine.process(observation(1, Zone.A, IdentityStatus.NOT_EVALUATED)) is None


def test_unknown_incoming_alarms_once() -> None:
    engine = PolicyEngine(SETTINGS)
    enter_a(engine)
    results = [engine.process(observation(i, Zone.B, IdentityStatus.UNKNOWN, Direction.INCOMING)) for i in range(2, 7)]
    alarms = [result for result in results if result and result.level == EventLevel.ALARM]
    assert len(alarms) == 1


def test_known_incoming_is_info() -> None:
    engine = PolicyEngine(SETTINGS)
    enter_a(engine)
    results = [engine.process(observation(i, Zone.B, IdentityStatus.KNOWN, Direction.INCOMING)) for i in range(2, 5)]
    assert results[-1] is not None
    assert results[-1].level == EventLevel.INFO
    assert results[-1].person_id == "person-1"


def test_direct_b_warns_but_never_alarms() -> None:
    engine = PolicyEngine(SETTINGS)
    results = [engine.process(observation(i, Zone.B, IdentityStatus.UNKNOWN)) for i in range(3)]
    assert sum(result is not None for result in results) == 1
    assert results[0].level == EventLevel.WARNING


def test_outgoing_does_not_alarm() -> None:
    engine = PolicyEngine(SETTINGS)
    results = [engine.process(observation(i, Zone.B, IdentityStatus.UNKNOWN, Direction.OUTGOING)) for i in range(3)]
    assert all(result is None or result.level != EventLevel.ALARM for result in results)


def test_low_quality_unknown_becomes_warning() -> None:
    engine = PolicyEngine(SETTINGS)
    enter_a(engine)
    observations = []
    for index in range(2, 5):
        item = observation(index, Zone.B, IdentityStatus.UNKNOWN, Direction.INCOMING)
        observations.append(engine.process(item.model_copy(update={"face_quality": 0.2})))
    assert observations[-1] is not None
    assert observations[-1].level == EventLevel.WARNING

