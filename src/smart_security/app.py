from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings, load_settings, project_root
from .database import Database
from .policy import PolicyEngine
from .schemas import (
    AckRequest,
    BuzzerCommand,
    CommandAction,
    EventLevel,
    ModeRequest,
    Observation,
    SystemMode,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or load_settings()
    cfg.server.data_dir.mkdir(parents=True, exist_ok=True)
    frame_dir = cfg.server.data_dir / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    db = Database(cfg.server.data_dir / "smart_security.db")
    policy = PolicyEngine(cfg.policy)

    api = FastAPI(title="Smart Security MVP", version="0.1.0")
    api.state.settings = cfg
    api.state.db = db
    api.state.policy = policy
    api.state.frame_dir = frame_dir
    api.state.last_buzzer_at = {}

    def verify_token(token: str | None) -> None:
        if cfg.device_token and token != cfg.device_token:
            raise HTTPException(status_code=401, detail="invalid device token")

    def issue_command(device_id: str, action: CommandAction) -> BuzzerCommand:
        now = datetime.now(timezone.utc)
        command = BuzzerCommand(
            device_id=device_id,
            action=action,
            duration_ms=cfg.buzzer.duration_ms if action == CommandAction.START else None,
            expires_at=now + timedelta(milliseconds=cfg.buzzer.command_ttl_ms),
            generation=db.next_generation(device_id),
        )
        db.insert_command(command)
        return command

    @api.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "version": api.version}

    @api.get("/api/v1/system")
    def get_system() -> dict:
        return {"mode": db.get_mode(), "config": {"vote_window": cfg.policy.vote_window, "required_votes": cfg.policy.required_votes}}

    @api.post("/api/v1/system/mode")
    def set_mode(request: ModeRequest) -> dict:
        db.set_mode(request.mode)
        policy.reset()
        commands = []
        if request.mode == SystemMode.DISARMED:
            commands = [issue_command(device["device_id"], CommandAction.STOP).model_dump(mode="json") for device in db.list_devices()]
        return {"mode": request.mode, "commands": commands}

    @api.post("/api/v1/system/silence")
    def silence() -> dict:
        commands = [issue_command(device["device_id"], CommandAction.STOP).model_dump(mode="json") for device in db.list_devices()]
        return {"silenced": True, "commands": commands}

    @api.post("/api/v1/devices/{device_id}/frames")
    async def upload_frame(
        device_id: str,
        frame: UploadFile = File(...),
        frame_id: str = Form(...),
        captured_at: datetime = Form(...),
        pir_active: bool = Form(...),
        x_device_token: str | None = Header(default=None),
    ) -> dict:
        verify_token(x_device_token)
        if frame.content_type not in {"image/jpeg", "image/jpg"}:
            raise HTTPException(status_code=415, detail="frame must be JPEG")
        payload = await frame.read()
        if len(payload) > 2_000_000:
            raise HTTPException(status_code=413, detail="frame too large")
        target = frame_dir / f"{device_id}.jpg"
        target.write_bytes(payload)
        db.touch_device(device_id, frame_id, captured_at.isoformat(), pir_active)
        return {"accepted": True, "frame_id": frame_id, "system_mode": db.get_mode()}

    @api.get("/api/v1/devices")
    def list_devices() -> list[dict]:
        return db.list_devices()

    @api.get("/api/v1/devices/{device_id}/latest-frame")
    def latest_frame(device_id: str) -> FileResponse:
        target = frame_dir / f"{device_id}.jpg"
        if not target.exists():
            raise HTTPException(status_code=404, detail="no frame")
        return FileResponse(target, media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    @api.post("/api/v1/observations")
    def add_observation(observation: Observation) -> dict:
        if db.get_mode() != SystemMode.ARMED:
            return {"accepted": False, "reason": "SYSTEM_NOT_ARMED", "event": None, "command": None}
        event_create = policy.process(observation)
        if event_create is None:
            return {"accepted": True, "event": None, "command": None}
        event = db.insert_event(event_create)
        command = None
        if event.level == EventLevel.ALARM:
            now = datetime.now(timezone.utc)
            last_buzzer_at = api.state.last_buzzer_at.get(observation.device_id)
            cooldown_elapsed = last_buzzer_at is None or (
                now - last_buzzer_at
            ).total_seconds() >= cfg.policy.device_cooldown_seconds
            if cooldown_elapsed:
                command = issue_command(observation.device_id, CommandAction.START)
                api.state.last_buzzer_at[observation.device_id] = now
        return {
            "accepted": True,
            "event": event.model_dump(mode="json"),
            "command": command.model_dump(mode="json") if command else None,
        }

    @api.get("/api/v1/events")
    def list_events(limit: int = 50) -> list[dict]:
        return db.list_events(max(1, min(limit, 200)))

    @api.post("/api/v1/events/{event_id}/ack")
    def acknowledge_event(event_id: str) -> dict:
        if not db.acknowledge_event(event_id):
            raise HTTPException(status_code=404, detail="event not found")
        return {"event_id": event_id, "acknowledged": True}

    @api.get("/api/v1/devices/{device_id}/commands")
    def list_commands(device_id: str, after_generation: int = 0, x_device_token: str | None = Header(default=None)) -> dict:
        verify_token(x_device_token)
        return {"commands": db.list_commands(device_id, after_generation)}

    @api.post("/api/v1/commands/{command_id}/ack")
    def acknowledge_command(command_id: str, request: AckRequest, x_device_token: str | None = Header(default=None)) -> dict:
        verify_token(x_device_token)
        if not db.acknowledge_command(command_id, request.status):
            raise HTTPException(status_code=404, detail="command not found")
        return {"command_id": command_id, "status": request.status}

    web_dir = project_root() / "src/smart_security/web"
    api.mount("/assets", StaticFiles(directory=web_dir), name="assets")

    @api.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(web_dir / "index.html")

    return api


app = create_app()
