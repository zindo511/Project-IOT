from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import Lock

from .schemas import BuzzerCommand, CommandStatus, Event, EventCreate, SystemMode


class Database:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS system_state (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    mode TEXT NOT NULL
                );
                INSERT OR REPLACE INTO system_state(singleton, mode) VALUES (1, 'DISARMED');

                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    visit_id TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    level TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    identity TEXT NOT NULL,
                    person_id TEXT,
                    occurred_at TEXT NOT NULL,
                    evidence_path TEXT,
                    acknowledged INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS commands (
                    command_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    duration_ms INTEGER,
                    expires_at TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    status TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    last_seen_at TEXT NOT NULL,
                    latest_frame_id TEXT,
                    pir_active INTEGER NOT NULL DEFAULT 0
                );
                """
            )

    def get_mode(self) -> SystemMode:
        with self._connect() as conn:
            row = conn.execute("SELECT mode FROM system_state WHERE singleton = 1").fetchone()
        return SystemMode(row["mode"])

    def set_mode(self, mode: SystemMode) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("UPDATE system_state SET mode = ? WHERE singleton = 1", (mode.value,))

    def insert_event(self, event: EventCreate) -> Event:
        with self._lock, self._connect() as conn:
            conn.execute(
                """INSERT INTO events
                (event_id, visit_id, device_id, level, reason, identity, person_id, occurred_at, evidence_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.event_id, event.visit_id, event.device_id, event.level.value,
                    event.reason.value, event.identity.value, event.person_id,
                    event.occurred_at.isoformat(), event.evidence_path,
                ),
            )
        return Event(**event.model_dump(), acknowledged=False)

    def list_events(self, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY occurred_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) | {"acknowledged": bool(row["acknowledged"])} for row in rows]

    def acknowledge_event(self, event_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute("UPDATE events SET acknowledged = 1 WHERE event_id = ?", (event_id,))
        return cur.rowcount == 1

    def next_generation(self, device_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(generation), 0) AS generation FROM commands WHERE device_id = ?",
                (device_id,),
            ).fetchone()
        return int(row["generation"]) + 1

    def insert_command(self, command: BuzzerCommand) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """INSERT INTO commands
                (command_id, device_id, action, duration_ms, expires_at, generation, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    command.command_id, command.device_id, command.action.value,
                    command.duration_ms, command.expires_at.isoformat(), command.generation,
                    command.status.value,
                ),
            )

    def list_commands(self, device_id: str, after_generation: int) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM commands WHERE device_id = ? AND generation > ?
                ORDER BY generation ASC""",
                (device_id, after_generation),
            ).fetchall()
        return [dict(row) for row in rows]

    def acknowledge_command(self, command_id: str, status: CommandStatus) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "UPDATE commands SET status = ? WHERE command_id = ?",
                (status.value, command_id),
            )
        return cur.rowcount == 1

    def touch_device(self, device_id: str, frame_id: str, captured_at: str, pir_active: bool) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """INSERT INTO devices(device_id, last_seen_at, latest_frame_id, pir_active)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    last_seen_at=excluded.last_seen_at,
                    latest_frame_id=excluded.latest_frame_id,
                    pir_active=excluded.pir_active""",
                (device_id, captured_at, frame_id, int(pir_active)),
            )

    def list_devices(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM devices ORDER BY device_id").fetchall()
        return [dict(row) | {"pir_active": bool(row["pir_active"])} for row in rows]

