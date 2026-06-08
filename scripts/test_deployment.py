#!/usr/bin/env python3
"""Regression tests for Docker deployment and secret handling."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from technews_briefing.deployment import (  # noqa: E402
    SENSITIVE_ENV_NAMES,
    DeploymentConfig,
    redacted_environment,
    render_health_text,
    run_deployment_health_check,
)
from technews_briefing.operations_console import hash_admin_password  # noqa: E402


def deployment_env(local_root: Path, sync_target: Path) -> dict[str, str]:
    return {
        "FEISHU_APP_ID": "dummy-feishu-app-id",
        "FEISHU_APP_SECRET": "dummy-feishu-app-secret",
        "FEISHU_TENANT_KEY": "dummy-feishu-tenant",
        "FEISHU_DEFAULT_USER_OPEN_ID": "dummy-feishu-user",
        "FEISHU_DEFAULT_CHAT_ID": "dummy-feishu-chat",
        "DELIVERY_DEADLINE_LOCAL_TIME": "08:00",
        "DELIVERY_TIMEZONE": "Asia/Shanghai",
        "FEISHU_GROUP_WEBHOOK_URL": "",
        "FEISHU_GROUP_WEBHOOK_SECRET": "",
        "MODEL_PROVIDER": "fixture-provider",
        "MODEL_API_KEY": "dummy-model-api-key",
        "MODEL_DEFAULT_MODEL": "fixture-model",
        "ARCHIVE_LOCAL_ROOT": str(local_root),
        "ARCHIVE_SYNC_TARGET": str(sync_target),
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD_HASH": hash_admin_password("not-a-real-password", salt=b"deployment-test-salt"),
        "SESSION_SECRET": "session-secret-for-deployment-tests",
    }


def test_deployment_health_passes_with_required_configuration() -> None:
    with TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        env = deployment_env(tmp / "archives", tmp / "sync-target")
        config = DeploymentConfig.from_env(env, data_dir=tmp / "data")

        health = run_deployment_health_check(config)

        assert health.status == "ok"
        assert (tmp / "data" / "operations.sqlite3").exists()
        assert (tmp / "archives").is_dir()
        assert (tmp / "sync-target").is_dir()


def test_deployment_health_reports_missing_or_invalid_inputs_without_values() -> None:
    with TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        env = deployment_env(tmp / "archives", tmp / "sync-target")
        env["MODEL_API_KEY"] = ""
        env["DELIVERY_DEADLINE_LOCAL_TIME"] = "8am"
        config = DeploymentConfig.from_env(env, data_dir=tmp / "data")

        health = run_deployment_health_check(config)
        text = render_health_text(health)

        assert health.status == "degraded"
        assert "MODEL_API_KEY" in text
        assert "DELIVERY_DEADLINE_LOCAL_TIME" in text
        assert "dummy-feishu-app-secret" not in text
        assert str(tmp) not in text


def test_deployment_health_redacts_secret_and_path_values() -> None:
    with TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        env = deployment_env(tmp / "archives", tmp / "sync-target")
        health = run_deployment_health_check(DeploymentConfig.from_env(env, data_dir=tmp / "data"))

        payload = json.dumps(health.as_mapping(), sort_keys=True)
        text = render_health_text(health)

        for name, value in env.items():
            if name in SENSITIVE_ENV_NAMES and value:
                assert value not in payload
                assert value not in text
        redacted = redacted_environment(env)
        assert redacted["MODEL_API_KEY"]["display_value"] == "REDACTED"
        assert redacted["ARCHIVE_LOCAL_ROOT"]["display_value"] == "REDACTED"


def test_compose_declares_required_runtime_surface() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "technews-briefing" in compose
    assert "python -m technews_briefing.deployment health --require-configured" in compose
    assert "technews-data:/var/lib/technews/data" in compose
    for name in deployment_env(Path("/tmp/archive-root"), Path("/tmp/sync-target")):
        assert name in compose
    assert "${ARCHIVE_LOCAL_ROOT:?" in compose
    assert "${ARCHIVE_SYNC_TARGET:?" in compose


def test_compose_config_validates_when_docker_is_available() -> None:
    if shutil.which("docker") is None:
        print("SKIP docker compose config validation: docker CLI is not installed")
        return

    with TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        env_path = tmp / "compose.env"
        env = deployment_env(tmp / "archives", tmp / "sync-target")
        assert "$" not in env["ADMIN_PASSWORD_HASH"]
        env_path.write_text("\n".join(f"{key}={value}" for key, value in env.items()) + "\n", encoding="utf-8")
        completed = subprocess.run(
            ["docker", "compose", "--env-file", str(env_path), "-f", "docker-compose.yml", "config", "--quiet"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr


def test_container_health_smoke_when_docker_daemon_is_available() -> None:
    if shutil.which("docker") is None:
        print("SKIP container health smoke: docker CLI is not installed")
        return

    info = subprocess.run(
        ["docker", "info", "--format", "{{.ServerVersion}}"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if info.returncode != 0:
        print("SKIP container health smoke: docker daemon is not available")
        return

    with TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        env_path = tmp / "compose.env"
        project_name = f"technews-deployment-test-{uuid4().hex[:12]}"
        env = deployment_env(tmp / "archives", tmp / "sync-target")
        assert "$" not in env["ADMIN_PASSWORD_HASH"]
        env_path.write_text("\n".join(f"{key}={value}" for key, value in env.items()) + "\n", encoding="utf-8")
        base_command = [
            "docker",
            "compose",
            "--project-name",
            project_name,
            "--env-file",
            str(env_path),
            "-f",
            "docker-compose.yml",
        ]
        try:
            completed = subprocess.run(
                [
                    *base_command,
                    "run",
                    "--rm",
                    "--build",
                    "--no-deps",
                    "technews-briefing",
                    "python",
                    "-m",
                    "technews_briefing.deployment",
                    "health",
                    "--require-configured",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            assert completed.returncode == 0, completed.stderr
            assert "status=ok" in completed.stdout
            assert env["MODEL_API_KEY"] not in completed.stdout
        finally:
            subprocess.run(
                [*base_command, "down", "--volumes", "--remove-orphans"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )


def main() -> int:
    tests = [
        test_deployment_health_passes_with_required_configuration,
        test_deployment_health_reports_missing_or_invalid_inputs_without_values,
        test_deployment_health_redacts_secret_and_path_values,
        test_compose_declares_required_runtime_surface,
        test_compose_config_validates_when_docker_is_available,
        test_container_health_smoke_when_docker_daemon_is_available,
    ]
    for test in tests:
        test()
    print("deployment tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
