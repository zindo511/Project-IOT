from dataclasses import replace
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from smart_security.app import create_app
from smart_security.config import load_settings


def test_server_starts_disarmed_and_serves_dashboard(tmp_path) -> None:
    base = load_settings()
    settings = replace(base, server=replace(base.server, data_dir=tmp_path))
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        assert client.get("/api/v1/system").json()["mode"] == "DISARMED"
        assert client.get("/").status_code == 200


def test_frame_contract(tmp_path) -> None:
    base = load_settings()
    settings = replace(base, server=replace(base.server, data_dir=tmp_path))
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/devices/door-01/frames",
            files={"frame": ("frame.jpg", b"fake-jpeg", "image/jpeg")},
            data={
                "frame_id": "1",
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "pir_active": "false",
            },
        )
        assert response.status_code == 200
        assert response.json()["accepted"] is True
        assert client.get("/api/v1/devices").json()[0]["device_id"] == "door-01"

