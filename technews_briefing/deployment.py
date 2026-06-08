"""Docker deployment configuration and health checks."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Mapping, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .operations_console import OperationsConsoleStore


DEFAULT_DATA_DIR = Path("/var/lib/technews/data")
DEFAULT_HEALTH_PORT = 8080
DEADLINE_PATTERN = re.compile(r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
REDACTED_VALUE = "REDACTED"
REQUIRED_ENV_GROUPS = {
    "delivery_schedule": (
        "DELIVERY_DEADLINE_LOCAL_TIME",
        "DELIVERY_TIMEZONE",
    ),
    "feishu_delivery": (
        "FEISHU_APP_ID",
        "FEISHU_APP_SECRET",
        "FEISHU_DEFAULT_USER_OPEN_ID",
        "FEISHU_DEFAULT_CHAT_ID",
    ),
    "model_provider": (
        "MODEL_PROVIDER",
        "MODEL_DEFAULT_MODEL",
        "MODEL_API_KEY",
    ),
    "archive_storage": (
        "ARCHIVE_LOCAL_ROOT",
        "ARCHIVE_SYNC_TARGET",
    ),
    "operations_console": (
        "ADMIN_USERNAME",
        "ADMIN_PASSWORD_HASH",
        "SESSION_SECRET",
    ),
}
OPTIONAL_ENV_NAMES = (
    "FEISHU_TENANT_KEY",
    "FEISHU_GROUP_WEBHOOK_URL",
    "FEISHU_GROUP_WEBHOOK_SECRET",
)
KNOWN_ENV_NAMES = tuple(
    dict.fromkeys(
        (
            *OPTIONAL_ENV_NAMES,
            *(name for group in REQUIRED_ENV_GROUPS.values() for name in group),
        )
    )
)
SENSITIVE_ENV_NAMES = {
    "FEISHU_APP_ID",
    "FEISHU_APP_SECRET",
    "FEISHU_TENANT_KEY",
    "FEISHU_DEFAULT_USER_OPEN_ID",
    "FEISHU_DEFAULT_CHAT_ID",
    "FEISHU_GROUP_WEBHOOK_URL",
    "FEISHU_GROUP_WEBHOOK_SECRET",
    "MODEL_API_KEY",
    "ARCHIVE_LOCAL_ROOT",
    "ARCHIVE_SYNC_TARGET",
    "ADMIN_PASSWORD_HASH",
    "SESSION_SECRET",
}


@dataclass(frozen=True)
class DeploymentConfig:
    environment: Mapping[str, str]
    data_dir: Path = DEFAULT_DATA_DIR

    @classmethod
    def from_env(
        cls,
        environment: Mapping[str, str] | None = None,
        *,
        data_dir: Path | str | None = None,
    ) -> "DeploymentConfig":
        values = dict(os.environ if environment is None else environment)
        configured_data_dir = data_dir or values.get("TECHNEWS_DATA_DIR") or DEFAULT_DATA_DIR
        return cls(environment=values, data_dir=Path(configured_data_dir))

    def value(self, name: str) -> str:
        return self.environment.get(name, "").strip()


@dataclass(frozen=True)
class HealthCheck:
    name: str
    status: str
    summary: str

    def as_mapping(self) -> dict[str, str]:
        return {
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class DeploymentHealth:
    checks: tuple[HealthCheck, ...]
    configuration: Mapping[str, object]

    @property
    def status(self) -> str:
        if all(check.status == "pass" for check in self.checks):
            return "ok"
        return "degraded"

    def as_mapping(self) -> dict[str, object]:
        return {
            "status": self.status,
            "checks": [check.as_mapping() for check in self.checks],
            "configuration": dict(self.configuration),
        }


def run_deployment_health_check(config: DeploymentConfig | None = None) -> DeploymentHealth:
    active_config = config or DeploymentConfig.from_env()
    checks = (
        _delivery_schedule_check(active_config),
        _required_group_check(active_config, "feishu_delivery"),
        _required_group_check(active_config, "model_provider"),
        _operations_console_check(active_config),
        _archive_write_check(active_config, "ARCHIVE_LOCAL_ROOT", "archive_write_path"),
        _archive_write_check(active_config, "ARCHIVE_SYNC_TARGET", "archive_sync_target"),
        _operations_store_check(active_config),
    )
    return DeploymentHealth(
        checks=checks,
        configuration=redacted_environment(active_config.environment),
    )


def redacted_environment(environment: Mapping[str, str]) -> dict[str, object]:
    redacted: dict[str, object] = {}
    for name in KNOWN_ENV_NAMES:
        value = environment.get(name, "").strip()
        if name in SENSITIVE_ENV_NAMES:
            redacted[name] = {
                "configured": bool(value),
                "display_value": REDACTED_VALUE if value else "UNSET",
            }
        else:
            redacted[name] = value
    return redacted


def render_health_text(health: DeploymentHealth) -> str:
    lines = [f"status={health.status}"]
    lines.extend(f"{check.name}={check.status} - {check.summary}" for check in health.checks)
    return "\n".join(lines) + "\n"


def _delivery_schedule_check(config: DeploymentConfig) -> HealthCheck:
    missing = _missing_names(config, REQUIRED_ENV_GROUPS["delivery_schedule"])
    if missing:
        return HealthCheck("delivery_schedule", "fail", f"missing {', '.join(missing)}")

    deadline = config.value("DELIVERY_DEADLINE_LOCAL_TIME")
    timezone_name = config.value("DELIVERY_TIMEZONE")
    if not DEADLINE_PATTERN.match(deadline):
        return HealthCheck("delivery_schedule", "fail", "DELIVERY_DEADLINE_LOCAL_TIME must use HH:MM")
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return HealthCheck("delivery_schedule", "fail", "DELIVERY_TIMEZONE must be an IANA timezone")
    return HealthCheck("delivery_schedule", "pass", "daily schedule can be evaluated")


def _required_group_check(config: DeploymentConfig, group_name: str) -> HealthCheck:
    missing = _missing_names(config, REQUIRED_ENV_GROUPS[group_name])
    if missing:
        return HealthCheck(group_name, "fail", f"missing {', '.join(missing)}")
    return HealthCheck(group_name, "pass", "required configuration is present")


def _operations_console_check(config: DeploymentConfig) -> HealthCheck:
    missing = _missing_names(config, REQUIRED_ENV_GROUPS["operations_console"])
    if missing:
        return HealthCheck("operations_console", "fail", f"missing {', '.join(missing)}")

    if len(config.value("SESSION_SECRET")) < 16:
        return HealthCheck("operations_console", "fail", "SESSION_SECRET must be at least 16 characters")
    if not _valid_pbkdf2_hash(config.value("ADMIN_PASSWORD_HASH")):
        return HealthCheck("operations_console", "fail", "ADMIN_PASSWORD_HASH must use pbkdf2_sha256 format")
    return HealthCheck("operations_console", "pass", "administrator auth configuration is usable")


def _archive_write_check(config: DeploymentConfig, env_name: str, check_name: str) -> HealthCheck:
    configured_path = config.value(env_name)
    if not configured_path:
        return HealthCheck(check_name, "fail", f"missing {env_name}")

    target = Path(configured_path).expanduser()
    if not target.is_absolute():
        return HealthCheck(check_name, "fail", f"{env_name} must be an absolute path")

    probe = target / ".technews-healthcheck.tmp"
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink()
    except OSError:
        return HealthCheck(check_name, "fail", f"{env_name} is not writable")
    return HealthCheck(check_name, "pass", f"{env_name} is writable")


def _operations_store_check(config: DeploymentConfig) -> HealthCheck:
    try:
        config.data_dir.mkdir(parents=True, exist_ok=True)
        store = OperationsConsoleStore(config.data_dir / "operations.sqlite3")
        try:
            store.initialize()
        finally:
            store.close()
    except OSError:
        return HealthCheck("operations_store", "fail", "data volume is not writable")
    return HealthCheck("operations_store", "pass", "SQLite operations store can initialize")


def _missing_names(config: DeploymentConfig, names: Sequence[str]) -> list[str]:
    return [name for name in names if not config.value(name)]


def _valid_pbkdf2_hash(value: str) -> bool:
    try:
        delimiter = ":" if ":" in value else "$"
        algorithm, iterations_raw, salt_raw, digest_raw = value.split(delimiter, 3)
        if algorithm != "pbkdf2_sha256":
            return False
        if int(iterations_raw) < 1:
            return False
        _b64decode(salt_raw)
        _b64decode(digest_raw)
    except (ValueError, TypeError):
        return False
    return True


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _health_handler(config: DeploymentConfig) -> type[BaseHTTPRequestHandler]:
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path != "/healthz":
                self.send_response(404)
                self.end_headers()
                return

            health = run_deployment_health_check(config)
            payload = json.dumps(health.as_mapping(), sort_keys=True).encode("utf-8")
            self.send_response(200 if health.status == "ok" else 503)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    return HealthHandler


def serve_health(config: DeploymentConfig, *, host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), _health_handler(config))
    server.serve_forever()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TechNews Briefing deployment helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    health = subparsers.add_parser("health", help="Run redacted deployment health checks")
    health.add_argument("--format", choices=("text", "json"), default="text")
    health.add_argument("--require-configured", action="store_true")

    serve = subparsers.add_parser("serve", help="Serve /healthz for the Docker Compose service")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=int(os.environ.get("TECHNEWS_HEALTH_PORT", DEFAULT_HEALTH_PORT)))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = DeploymentConfig.from_env()

    if args.command == "health":
        health = run_deployment_health_check(config)
        if args.format == "json":
            print(json.dumps(health.as_mapping(), indent=2, sort_keys=True))
        else:
            print(render_health_text(health), end="")
        return 0 if health.status == "ok" or not args.require_configured else 1

    if args.command == "serve":
        serve_health(config, host=args.host, port=args.port)
        return 0

    raise AssertionError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
