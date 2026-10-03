from __future__ import annotations

import argparse
import io
import time
from datetime import datetime, timezone

import requests
from PIL import Image, ImageDraw


def make_jpeg(label: str, step: int) -> bytes:
    image = Image.new("RGB", (640, 480), "#1f2937")
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 180, 360, 450), outline="#38bdf8", width=4)
    draw.rectangle((390, 180, 610, 450), outline="#fb7185", width=4)
    draw.text((60, 200), "ZONE A", fill="white")
    draw.text((410, 200), "ZONE B", fill="white")
    draw.text((60, 50), f"{label} / frame {step}", fill="white")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=80)
    return buffer.getvalue()


def scenario_steps(name: str) -> list[tuple[str, str, str, str | None]]:
    if name == "known":
        return [("A", "UNKNOWN", "NOT_EVALUATED", None)] * 2 + [("B", "INCOMING", "KNOWN", "person-demo")] * 3
    if name == "unknown":
        return [("A", "UNKNOWN", "NOT_EVALUATED", None)] * 2 + [("B", "INCOMING", "UNKNOWN", None)] * 3
    if name == "direct-b":
        return [("B", "UNKNOWN", "UNKNOWN", None)] * 3
    if name == "outgoing":
        return [("B", "OUTGOING", "UNKNOWN", None)] * 2 + [("A", "OUTGOING", "NOT_EVALUATED", None)] * 2
    raise ValueError(name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Smart Security device + vision simulator")
    parser.add_argument("--server", default="http://127.0.0.1:8000")
    parser.add_argument("--device", default="door-01")
    parser.add_argument("--scenario", choices=["known", "unknown", "direct-b", "outgoing"], default="unknown")
    parser.add_argument("--token", default=None)
    args = parser.parse_args()

    session = requests.Session()
    headers = {"X-Device-Token": args.token} if args.token else {}
    session.post(f"{args.server}/api/v1/system/mode", json={"mode": "ARMED"}, timeout=5).raise_for_status()
    track_id = f"sim-{args.scenario}-{int(time.time())}"
    generation = 0

    for index, (zone, direction, identity, person_id) in enumerate(scenario_steps(args.scenario), 1):
        captured_at = datetime.now(timezone.utc).isoformat()
        frame_id = f"{track_id}-{index}"
        frame_response = session.post(
            f"{args.server}/api/v1/devices/{args.device}/frames",
            headers=headers,
            files={"frame": ("frame.jpg", make_jpeg(args.scenario, index), "image/jpeg")},
            data={"frame_id": frame_id, "captured_at": captured_at, "pir_active": "true"},
            timeout=5,
        )
        frame_response.raise_for_status()
        observation = {
            "device_id": args.device,
            "frame_id": frame_id,
            "captured_at": captured_at,
            "track_id": track_id,
            "zone": zone,
            "direction": direction,
            "face_quality": 0.9 if identity in {"KNOWN", "UNKNOWN"} else 0.0,
            "identity": identity,
            "person_id": person_id,
            "match_score": 0.8 if identity == "KNOWN" else (0.2 if identity == "UNKNOWN" else None),
        }
        result = session.post(f"{args.server}/api/v1/observations", json=observation, timeout=5)
        result.raise_for_status()
        print(f"frame {index}: zone={zone}, identity={identity}, result={result.json()}")
        time.sleep(0.3)

    commands = session.get(
        f"{args.server}/api/v1/devices/{args.device}/commands",
        params={"after_generation": generation}, headers=headers, timeout=5,
    ).json()["commands"]
    for command in commands:
        print(f"BUZZER {command['action']} generation={command['generation']}")
        session.post(
            f"{args.server}/api/v1/commands/{command['command_id']}/ack",
            headers=headers,
            json={"device_id": args.device, "status": "ACKED"},
            timeout=5,
        ).raise_for_status()


if __name__ == "__main__":
    main()

