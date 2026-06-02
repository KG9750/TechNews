#!/usr/bin/env python3
"""Throwaway Feishu delivery spike runner.

This script is intentionally kept outside product code. It sends the fixture
Push Briefing card to one Feishu user and one Feishu group when credentials are
available, and writes redacted evidence under evidence/feishu-delivery/.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
CARD_PATH = ROOT / "fixtures/feishu-delivery/push-briefing-card-content.json"
RENDERED_PATH = ROOT / "fixtures/feishu-delivery/rendered-message.md"
DEFAULT_EVIDENCE_DIR = ROOT / "evidence/feishu-delivery"
FEISHU_BASE_URL = "https://open.feishu.cn"


class SpikeError(Exception):
    pass


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def required_env(names: list[str]) -> dict[str, str]:
    values = {name: os.environ.get(name, "") for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise SpikeError("missing environment variables: " + ", ".join(missing))
    return values


def request_json(method: str, url: str, payload: dict, headers: dict[str, str]) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            text = response.read().decode("utf-8")
            return json.loads(text)
    except HTTPError as error:
        text = error.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = {"raw": text}
        parsed["_http_status"] = error.code
        return parsed


def get_tenant_access_token(app_id: str, app_secret: str) -> tuple[str, dict]:
    response = request_json(
        "POST",
        f"{FEISHU_BASE_URL}/open-apis/auth/v3/tenant_access_token/internal",
        {"app_id": app_id, "app_secret": app_secret},
        {"Content-Type": "application/json"},
    )
    token = response.get("tenant_access_token")
    if not token:
        raise SpikeError("tenant token request failed; see redacted evidence")
    return token, response


def build_message_request(receive_id: str, card: dict) -> dict:
    return {
        "receive_id": receive_id,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False),
    }


def send_message(token: str, receive_id_type: str, receive_id: str, card: dict) -> tuple[dict, dict]:
    payload = build_message_request(receive_id, card)
    response = request_json(
        "POST",
        f"{FEISHU_BASE_URL}/open-apis/im/v1/messages?receive_id_type={receive_id_type}",
        payload,
        {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    return payload, response


def redact(value):
    if isinstance(value, dict):
        redacted = {}
        for key, child in value.items():
            lowered = key.lower()
            if any(part in lowered for part in ["secret", "token", "authorization", "receive_id"]):
                redacted[key] = "REDACTED"
            else:
                redacted[key] = redact(child)
        return redacted
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(dry_run: bool, evidence_dir: Path) -> int:
    load_env_file(ROOT / ".env")
    card = json.loads(CARD_PATH.read_text(encoding="utf-8"))
    evidence_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(RENDERED_PATH, evidence_dir / "rendered-message.md")

    if dry_run:
        request_shape = {
            "user_delivery": {
                "receive_id_type": "open_id",
                "body": build_message_request("${FEISHU_DEFAULT_USER_OPEN_ID}", card),
            },
            "group_delivery": {
                "receive_id_type": "chat_id",
                "body": build_message_request("${FEISHU_DEFAULT_CHAT_ID}", card),
            },
            "dry_run": True,
            "generated_at_epoch": int(time.time()),
        }
        write_json(evidence_dir / "dry-run-request-shape.redacted.json", redact(request_shape))
        print(f"DRY-RUN wrote redacted request shape to {evidence_dir}")
        return 0

    env = required_env(
        [
            "FEISHU_APP_ID",
            "FEISHU_APP_SECRET",
            "FEISHU_DEFAULT_USER_OPEN_ID",
            "FEISHU_DEFAULT_CHAT_ID",
        ]
    )
    token = ""
    token_response: dict = {}
    try:
        token, token_response = get_tenant_access_token(env["FEISHU_APP_ID"], env["FEISHU_APP_SECRET"])
    finally:
        write_json(evidence_dir / "tenant-token-response.redacted.json", redact(token_response))

    results = {}
    for name, receive_id_type, env_name in [
        ("user", "open_id", "FEISHU_DEFAULT_USER_OPEN_ID"),
        ("group", "chat_id", "FEISHU_DEFAULT_CHAT_ID"),
    ]:
        request_payload, response = send_message(token, receive_id_type, env[env_name], card)
        results[name] = response
        write_json(evidence_dir / f"{name}-request.redacted.json", redact(request_payload))
        write_json(evidence_dir / f"{name}-response.redacted.json", redact(response))

    failed = {name: response for name, response in results.items() if response.get("code") != 0}
    if failed:
        print("LIVE send completed with Feishu errors; inspect redacted evidence")
        return 2
    print(f"LIVE send evidence written to {evidence_dir}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Validate payload shape without credentials or network.")
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR))
    args = parser.parse_args()
    try:
        return run(dry_run=args.dry_run, evidence_dir=Path(args.evidence_dir))
    except SpikeError as error:
        print(f"ERROR {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
