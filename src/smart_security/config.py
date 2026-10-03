from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ServerSettings:
    host: str
    port: int
    data_dir: Path
    device_token_env: str


@dataclass(frozen=True)
class PolicySettings:
    vote_window: int
    required_votes: int
    min_zone_observations: int
    min_vote_spacing_ms: int
    min_face_quality: float
    track_timeout_seconds: float
    device_cooldown_seconds: float


@dataclass(frozen=True)
class BuzzerSettings:
    duration_ms: int
    hard_cap_ms: int
    command_ttl_ms: int
    control_timeout_ms: int


@dataclass(frozen=True)
class Settings:
    server: ServerSettings
    policy: PolicySettings
    buzzer: BuzzerSettings
    raw: dict[str, Any]

    @property
    def device_token(self) -> str | None:
        return os.getenv(self.server.device_token_env) or None


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_settings(path: str | Path | None = None, data_dir: str | Path | None = None) -> Settings:
    config_path = Path(path or os.getenv("SMART_SECURITY_CONFIG", project_root() / "config/default.yaml"))
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    resolved_data_dir = Path(data_dir or raw["server"]["data_dir"])
    if not resolved_data_dir.is_absolute():
        resolved_data_dir = project_root() / resolved_data_dir

    return Settings(
        server=ServerSettings(
            host=str(raw["server"]["host"]),
            port=int(raw["server"]["port"]),
            data_dir=resolved_data_dir,
            device_token_env=str(raw["server"]["device_token_env"]),
        ),
        policy=PolicySettings(**raw["policy"]),
        buzzer=BuzzerSettings(**raw["buzzer"]),
        raw=raw,
    )
