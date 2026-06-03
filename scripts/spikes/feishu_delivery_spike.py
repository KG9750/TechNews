#!/usr/bin/env python3
"""Throwaway Feishu delivery spike runner.

This script is intentionally kept outside product code. It sends the fixture
Push Briefing card to one Feishu user and one Feishu group when credentials are
available, and writes redacted evidence under evidence/feishu-delivery/.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
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
SENSITIVE_KEY_PARTS = [
    "authorization",
    "secret",
    "token",
    "tenant",
]
SENSITIVE_KEY_EXACT = {
    "receive_id",
    "open_id",
    "chat_id",
    "app_id",
    "sign",
}
SENSITIVE_VALUE_PATTERNS = [
    re.compile(r"Authorization\s*[:=]\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
    re.compile(r"\bou_[A-Za-z0-9]{8,}\b"),
    re.compile(r"\boc_[A-Za-z0-9]{8,}\b"),
    re.compile(r"\bcli_[A-Za-z0-9]{8,}\b"),
    re.compile(r"https://open\.(?:feishu|larksuite)\.cn/open-apis/bot/v2/hook/[A-Za-z0-9_-]+", re.IGNORECASE),
]
SENSITIVE_ENV_NAMES = [
    "FEISHU_APP_ID",
    "FEISHU_APP_SECRET",
    "FEISHU_TENANT_KEY",
    "FEISHU_DEFAULT_USER_OPEN_ID",
    "FEISHU_DEFAULT_CHAT_ID",
    "FEISHU_GROUP_WEBHOOK_URL",
    "FEISHU_GROUP_WEBHOOK_SECRET",
]


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


def build_internal_app_request_evidence(receive_id_type: str, payload: dict) -> dict:
    return {
        "path": "internal_app_bot",
        "receive_id_type": receive_id_type,
        "body": payload,
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


def build_group_webhook_sign(timestamp: int, secret: str) -> str:
    string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
    digest = hmac.new(string_to_sign, digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def build_group_webhook_payload(card: dict, secret: str = "", timestamp: int | None = None) -> dict:
    payload = {
        "msg_type": "interactive",
        "card": card,
    }
    if secret:
        actual_timestamp = timestamp if timestamp is not None else int(time.time())
        payload["timestamp"] = str(actual_timestamp)
        payload["sign"] = build_group_webhook_sign(actual_timestamp, secret)
    return payload


def build_group_webhook_dry_run_shape(card: dict) -> dict:
    payload = build_group_webhook_payload(card, secret="DRY_RUN_SIGNING_SECRET", timestamp=0)
    return {
        "path": "custom_group_bot_fallback",
        "attempted_by_default": False,
        "requires_explicit_flag": "--attempt-group-webhook-fallback",
        "does_not_satisfy_personal_delivery": True,
        "does_not_replace_internal_app_group_evidence": True,
        "body": payload,
    }


def send_group_webhook(webhook_url: str, card: dict, secret: str = "") -> tuple[dict, dict]:
    payload = build_group_webhook_payload(card, secret=secret)
    response = request_json(
        "POST",
        webhook_url,
        payload,
        {"Content-Type": "application/json"},
    )
    return payload, response


def redact(value):
    if isinstance(value, dict):
        redacted = {}
        for key, child in value.items():
            lowered = key.lower()
            if lowered in SENSITIVE_KEY_EXACT or any(part in lowered for part in SENSITIVE_KEY_PARTS):
                redacted[key] = "REDACTED"
            else:
                redacted[key] = redact(child)
        return redacted
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        for pattern in SENSITIVE_VALUE_PATTERNS:
            if pattern.search(value):
                return "REDACTED"
    return value


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_evidence_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_evidence_redaction(path: Path) -> None:
    text = read_evidence_text(path)
    if "TEMPLATE_" in text:
        raise SpikeError(f"{path}: evidence still contains TEMPLATE_ placeholder")
    for pattern in SENSITIVE_VALUE_PATTERNS:
        if pattern.search(text):
            raise SpikeError(f"{path}: evidence may leak Feishu token, id, or webhook value")
    for label, pattern in [
        ("local user path", r"/Users/[^/\s\"]+"),
        ("private tmp path", r"(?<![A-Za-z0-9_./-])/private/"),
        ("iCloud workspace path", r"Mobile Documents/com~apple~CloudDocs"),
    ]:
        if re.search(pattern, text):
            raise SpikeError(f"{path}: evidence may leak {label}")
    for env_name in SENSITIVE_ENV_NAMES:
        value = os.environ.get(env_name, "")
        if len(value) >= 8 and value in text:
            raise SpikeError(f"{path}: evidence contains raw environment value {env_name}")


def validate_delivery_response(path: Path, label: str) -> None:
    if not path.exists():
        raise SpikeError(f"missing Feishu {label} response evidence: {path}")
    check_evidence_redaction(path)
    payload = json.loads(read_evidence_text(path))
    if payload.get("code") != 0:
        raise SpikeError(f"{path}: Feishu {label} response code must be 0")
    data = payload.get("data", {})
    if not isinstance(data, dict) or not data:
        raise SpikeError(f"{path}: Feishu {label} response must include data")
    message_id = data.get("message_id")
    if not isinstance(message_id, str) or not message_id.strip():
        raise SpikeError(f"{path}: Feishu {label} response must include data.message_id")


def validate_delivery_request(path: Path, label: str, expected_receive_id_type: str) -> None:
    if not path.exists():
        raise SpikeError(f"missing Feishu {label} request evidence: {path}")
    check_evidence_redaction(path)
    payload = json.loads(read_evidence_text(path))
    if payload.get("path") != "internal_app_bot":
        raise SpikeError(f"{path}: Feishu {label} request path must be internal_app_bot")
    if payload.get("receive_id_type") != expected_receive_id_type:
        raise SpikeError(f"{path}: Feishu {label} request receive_id_type must be {expected_receive_id_type}")
    body = payload.get("body", {})
    if not isinstance(body, dict):
        raise SpikeError(f"{path}: Feishu {label} request body must be an object")
    if body.get("msg_type") != "interactive":
        raise SpikeError(f"{path}: Feishu {label} request msg_type must be interactive")
    if not body.get("receive_id"):
        raise SpikeError(f"{path}: Feishu {label} request must include redacted receive_id")
    content = body.get("content")
    if not isinstance(content, str) or not content.strip():
        raise SpikeError(f"{path}: Feishu {label} request must include card content")
    try:
        json.loads(content)
    except json.JSONDecodeError as error:
        raise SpikeError(f"{path}: Feishu {label} request content must be JSON") from error


def validate_rendered_message(path: Path) -> None:
    if not path.exists():
        raise SpikeError(f"missing Feishu rendered message evidence: {path}")
    check_evidence_redaction(path)
    rendered = read_evidence_text(path)
    for needle in ["Source", "置信提示"]:
        if needle not in rendered:
            raise SpikeError(f"{path}: Feishu rendered message missing {needle}")
    if not any(needle in rendered for needle in ["Archive", "Deep-Dive", "Deep Dive", "归档"]):
        raise SpikeError(f"{path}: Feishu rendered message missing Archive or Deep-Dive link")


def validate_evidence(evidence_dir: Path) -> int:
    load_env_file(ROOT / ".env")
    validate_delivery_request(evidence_dir / "user-request.redacted.json", "user", "open_id")
    validate_delivery_request(evidence_dir / "group-request.redacted.json", "group", "chat_id")
    validate_delivery_response(evidence_dir / "user-response.redacted.json", "user")
    validate_delivery_response(evidence_dir / "group-response.redacted.json", "group")
    validate_rendered_message(evidence_dir / "rendered-message.md")
    print(f"LIVE Feishu evidence validates: {evidence_dir}")
    return 0


def run(dry_run: bool, evidence_dir: Path, attempt_group_webhook_fallback: bool = False) -> int:
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
            "group_webhook_fallback": build_group_webhook_dry_run_shape(card),
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
        write_json(
            evidence_dir / f"{name}-request.redacted.json",
            redact(build_internal_app_request_evidence(receive_id_type, request_payload)),
        )
        write_json(evidence_dir / f"{name}-response.redacted.json", redact(response))

    failed = {name: response for name, response in results.items() if response.get("code") != 0}
    if failed.get("group") and attempt_group_webhook_fallback:
        webhook_url = os.environ.get("FEISHU_GROUP_WEBHOOK_URL", "")
        webhook_secret = os.environ.get("FEISHU_GROUP_WEBHOOK_SECRET", "")
        if webhook_url:
            fallback_request, fallback_response = send_group_webhook(webhook_url, card, webhook_secret)
            write_json(evidence_dir / "group-fallback-request.redacted.json", redact(fallback_request))
            write_json(evidence_dir / "group-fallback-response.redacted.json", redact(fallback_response))
        else:
            write_json(
                evidence_dir / "group-fallback-skipped.redacted.json",
                {
                    "path": "custom_group_bot_fallback",
                    "status": "skipped",
                    "reason": "FEISHU_GROUP_WEBHOOK_URL is not configured.",
                },
            )
    if failed:
        print("LIVE send completed with Feishu errors; inspect redacted evidence")
        return 2
    print(f"LIVE send evidence written to {evidence_dir}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Validate payload shape without credentials or network.")
    parser.add_argument("--validate-evidence", action="store_true", help="Validate redacted live Feishu delivery evidence.")
    parser.add_argument(
        "--attempt-group-webhook-fallback",
        action="store_true",
        help="After internal app group delivery fails, try the optional custom group bot fallback. This does not satisfy the internal-app group evidence gate.",
    )
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR))
    args = parser.parse_args()
    try:
        if args.validate_evidence:
            return validate_evidence(Path(args.evidence_dir))
        return run(
            dry_run=args.dry_run,
            evidence_dir=Path(args.evidence_dir),
            attempt_group_webhook_fallback=args.attempt_group_webhook_fallback,
        )
    except (FileNotFoundError, json.JSONDecodeError, SpikeError) as error:
        print(f"ERROR {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
