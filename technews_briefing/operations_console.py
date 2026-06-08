"""Operations Console auth, store, and view-model primitives."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


class OperationsConsoleError(ValueError):
    """Raised when Operations Console inputs are invalid."""


SECRET_DISPLAY_VALUE = "REDACTED"
SESSION_ALGORITHM = "hmac_sha256"
TABLE_COLUMNS = {
    "sources": {"source_id", "name", "source_type", "eligibility_state", "connector_status", "last_checked_at"},
    "taxonomy": {"section", "subcategory"},
    "recipients": {"recipient_id", "recipient_type", "label", "enabled"},
    "subscriptions": {"recipient_id", "section", "subcategory"},
    "runs": {"run_id", "domain_template", "scheduled_for", "run_status", "archive_url"},
    "selected_items": {"run_id", "item_id", "title_zh", "section", "confidence_level", "selection_rationale"},
    "excluded_candidates": {"run_id", "candidate_id", "reason", "selection_rationale"},
    "delivery_status": {"run_id", "recipient_id", "status", "retryable", "failure_reason"},
    "sync_status": {"run_id", "target_key", "status", "retryable", "failure_reason"},
}
TABLE_ORDERINGS = {
    "sources": "source_id",
    "taxonomy": "section, subcategory",
    "recipients": "recipient_id",
    "subscriptions": "recipient_id, section, subcategory",
    "runs": "scheduled_for DESC, run_id",
    "selected_items": "run_id, item_id",
    "excluded_candidates": "run_id, candidate_id",
    "delivery_status": "run_id, recipient_id",
    "sync_status": "run_id, target_key",
}


@dataclass(frozen=True)
class AdminSession:
    username: str
    issued_at: int
    expires_at: int


@dataclass(frozen=True)
class ConsoleView:
    configuration: Mapping[str, object]
    sources: tuple[Mapping[str, object], ...]
    taxonomy: Mapping[str, tuple[str, ...]]
    recipients: tuple[Mapping[str, object], ...]
    subscriptions: tuple[Mapping[str, object], ...]
    runs: tuple[Mapping[str, object], ...]
    selected_items: tuple[Mapping[str, object], ...]
    excluded_candidates: tuple[Mapping[str, object], ...]
    delivery_status: tuple[Mapping[str, object], ...]
    sync_status: tuple[Mapping[str, object], ...]
    retry_actions: tuple[Mapping[str, object], ...]


def hash_admin_password(password: str, *, salt: bytes, iterations: int = 120_000) -> str:
    if not password:
        raise OperationsConsoleError("password must not be empty")
    if not salt:
        raise OperationsConsoleError("salt must not be empty")
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256${iterations}${salt}${digest}".format(
        iterations=iterations,
        salt=_b64encode(salt),
        digest=_b64encode(digest),
    )


def verify_admin_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt_raw, digest_raw = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        salt = _b64decode(salt_raw)
        expected = _b64decode(digest_raw)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


class AdminAuth:
    def __init__(self, *, username: str, password_hash: str, session_secret: str, session_ttl_seconds: int = 86400):
        if not username.strip():
            raise OperationsConsoleError("username must be a non-empty string")
        if not password_hash.strip():
            raise OperationsConsoleError("password_hash must be a non-empty string")
        if len(session_secret) < 16:
            raise OperationsConsoleError("session_secret must be at least 16 characters")
        self.username = username
        self.password_hash = password_hash
        self.session_secret = session_secret.encode("utf-8")
        self.session_ttl_seconds = session_ttl_seconds

    def login(self, username: str, password: str, *, now: int | None = None) -> str:
        if username != self.username or not verify_admin_password(password, self.password_hash):
            raise OperationsConsoleError("invalid administrator credentials")
        issued_at = int(time.time() if now is None else now)
        return self._sign_session(
            AdminSession(
                username=username,
                issued_at=issued_at,
                expires_at=issued_at + self.session_ttl_seconds,
            )
        )

    def verify_session(self, token: str, *, now: int | None = None) -> AdminSession:
        try:
            payload_raw, signature_raw = token.split(".", 1)
        except ValueError as error:
            raise OperationsConsoleError("invalid session token") from error
        expected_signature = self._signature(payload_raw)
        if not hmac.compare_digest(expected_signature, signature_raw):
            raise OperationsConsoleError("invalid session signature")
        payload = json.loads(_b64decode(payload_raw).decode("utf-8"))
        session = AdminSession(
            username=str(payload["username"]),
            issued_at=int(payload["issued_at"]),
            expires_at=int(payload["expires_at"]),
        )
        if session.username != self.username:
            raise OperationsConsoleError("invalid session subject")
        current_time = int(time.time() if now is None else now)
        if session.expires_at < current_time:
            raise OperationsConsoleError("session expired")
        return session

    def _sign_session(self, session: AdminSession) -> str:
        payload = _b64encode(
            json.dumps(
                {
                    "username": session.username,
                    "issued_at": session.issued_at,
                    "expires_at": session.expires_at,
                    "alg": SESSION_ALGORITHM,
                },
                separators=(",", ":"),
            ).encode("utf-8")
        )
        return f"{payload}.{self._signature(payload)}"

    def _signature(self, payload: str) -> str:
        return _b64encode(hmac.new(self.session_secret, payload.encode("utf-8"), hashlib.sha256).digest())


class OperationsConsoleStore:
    def __init__(self, database_path: Path | str = ":memory:") -> None:
        self.connection = sqlite3.connect(str(database_path))
        self.connection.row_factory = sqlite3.Row

    def close(self) -> None:
        self.connection.close()

    def initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS console_config (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL,
              is_secret INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS sources (
              source_id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              source_type TEXT NOT NULL,
              eligibility_state TEXT NOT NULL,
              connector_status TEXT NOT NULL,
              last_checked_at TEXT
            );
            CREATE TABLE IF NOT EXISTS taxonomy (
              section TEXT NOT NULL,
              subcategory TEXT NOT NULL,
              PRIMARY KEY (section, subcategory)
            );
            CREATE TABLE IF NOT EXISTS recipients (
              recipient_id TEXT PRIMARY KEY,
              recipient_type TEXT NOT NULL,
              label TEXT NOT NULL,
              enabled INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS subscriptions (
              recipient_id TEXT NOT NULL,
              section TEXT NOT NULL,
              subcategory TEXT,
              PRIMARY KEY (recipient_id, section, subcategory)
            );
            CREATE TABLE IF NOT EXISTS runs (
              run_id TEXT PRIMARY KEY,
              domain_template TEXT NOT NULL,
              scheduled_for TEXT NOT NULL,
              run_status TEXT NOT NULL,
              archive_url TEXT
            );
            CREATE TABLE IF NOT EXISTS selected_items (
              run_id TEXT NOT NULL,
              item_id TEXT NOT NULL,
              title_zh TEXT NOT NULL,
              section TEXT NOT NULL,
              confidence_level TEXT NOT NULL,
              selection_rationale TEXT NOT NULL,
              PRIMARY KEY (run_id, item_id)
            );
            CREATE TABLE IF NOT EXISTS excluded_candidates (
              run_id TEXT NOT NULL,
              candidate_id TEXT NOT NULL,
              reason TEXT NOT NULL,
              selection_rationale TEXT NOT NULL,
              PRIMARY KEY (run_id, candidate_id)
            );
            CREATE TABLE IF NOT EXISTS delivery_status (
              run_id TEXT NOT NULL,
              recipient_id TEXT NOT NULL,
              status TEXT NOT NULL,
              retryable INTEGER NOT NULL DEFAULT 0,
              failure_reason TEXT,
              PRIMARY KEY (run_id, recipient_id)
            );
            CREATE TABLE IF NOT EXISTS sync_status (
              run_id TEXT NOT NULL,
              target_key TEXT NOT NULL,
              status TEXT NOT NULL,
              retryable INTEGER NOT NULL DEFAULT 0,
              failure_reason TEXT,
              PRIMARY KEY (run_id, target_key)
            );
            """
        )
        self.connection.commit()

    def upsert_config(self, key: str, value: str, *, is_secret: bool = False) -> None:
        if not key.strip():
            raise OperationsConsoleError("configuration key must not be empty")
        self.connection.execute(
            """
            INSERT INTO console_config (key, value, is_secret)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, is_secret = excluded.is_secret
            """,
            (key, value, 1 if is_secret else 0),
        )
        self.connection.commit()

    def insert_many(self, table: str, rows: Iterable[Mapping[str, object]]) -> None:
        _require_allowed_table(table)
        rows = tuple(rows)
        if not rows:
            return
        columns = tuple(rows[0])
        unknown_columns = set(columns) - TABLE_COLUMNS[table]
        if unknown_columns:
            raise OperationsConsoleError(f"unknown columns for {table}: {', '.join(sorted(unknown_columns))}")
        placeholders = ", ".join("?" for _ in columns)
        column_sql = ", ".join(columns)
        self.connection.executemany(
            f"INSERT OR REPLACE INTO {table} ({column_sql}) VALUES ({placeholders})",
            [tuple(row[column] for column in columns) for row in rows],
        )
        self.connection.commit()

    def fetch_all(self, table: str, *, order_by: str) -> tuple[Mapping[str, object], ...]:
        _require_allowed_table(table)
        if TABLE_ORDERINGS[table] != order_by:
            raise OperationsConsoleError(f"unsupported ordering for {table}")
        rows = self.connection.execute(f"SELECT * FROM {table} ORDER BY {order_by}").fetchall()
        return tuple(_row_mapping(row) for row in rows)

    def configuration_view(self) -> dict[str, object]:
        rows = self.connection.execute("SELECT key, value, is_secret FROM console_config ORDER BY key").fetchall()
        values: dict[str, object] = {}
        for row in rows:
            key = str(row["key"])
            value = str(row["value"])
            if row["is_secret"]:
                values[key] = {
                    "configured": bool(value),
                    "display_value": SECRET_DISPLAY_VALUE if value else "UNSET",
                }
            else:
                values[key] = value
        return values


class OperationsConsole:
    def __init__(self, *, store: OperationsConsoleStore, auth: AdminAuth) -> None:
        self.store = store
        self.auth = auth

    def dashboard(self, session_token: str, *, now: int | None = None) -> ConsoleView:
        self.auth.verify_session(session_token, now=now)
        taxonomy = _taxonomy_view(self.store.fetch_all("taxonomy", order_by="section, subcategory"))
        delivery = self.store.fetch_all("delivery_status", order_by="run_id, recipient_id")
        sync = self.store.fetch_all("sync_status", order_by="run_id, target_key")
        return ConsoleView(
            configuration=self.store.configuration_view(),
            sources=self.store.fetch_all("sources", order_by="source_id"),
            taxonomy=taxonomy,
            recipients=self.store.fetch_all("recipients", order_by="recipient_id"),
            subscriptions=self.store.fetch_all("subscriptions", order_by="recipient_id, section, subcategory"),
            runs=self.store.fetch_all("runs", order_by="scheduled_for DESC, run_id"),
            selected_items=self.store.fetch_all("selected_items", order_by="run_id, item_id"),
            excluded_candidates=self.store.fetch_all("excluded_candidates", order_by="run_id, candidate_id"),
            delivery_status=delivery,
            sync_status=sync,
            retry_actions=_retry_actions(delivery, sync),
        )

    def update_configuration(
        self,
        session_token: str,
        key: str,
        value: str,
        *,
        is_secret: bool = False,
        now: int | None = None,
    ) -> None:
        self.auth.verify_session(session_token, now=now)
        self.store.upsert_config(key, value, is_secret=is_secret)


def seed_console_store(store: OperationsConsoleStore, seed: Mapping[str, Iterable[Mapping[str, object]]]) -> None:
    for table, rows in seed.items():
        if table == "console_config":
            for row in rows:
                store.upsert_config(str(row["key"]), str(row["value"]), is_secret=bool(row.get("is_secret", False)))
        else:
            store.insert_many(table, rows)


def _retry_actions(
    delivery_status: tuple[Mapping[str, object], ...],
    sync_status: tuple[Mapping[str, object], ...],
) -> tuple[Mapping[str, object], ...]:
    actions: list[Mapping[str, object]] = []
    for row in delivery_status:
        if row["status"] == "failed" and bool(row["retryable"]):
            actions.append(
                {
                    "action_id": f"retry_delivery:{row['run_id']}:{row['recipient_id']}",
                    "target_type": "delivery",
                    "run_id": row["run_id"],
                    "target_key": row["recipient_id"],
                    "label": "Retry Feishu delivery",
                }
            )
    for row in sync_status:
        if row["status"] == "failed" and bool(row["retryable"]):
            actions.append(
                {
                    "action_id": f"retry_sync:{row['run_id']}:{row['target_key']}",
                    "target_type": "sync",
                    "run_id": row["run_id"],
                    "target_key": row["target_key"],
                    "label": "Retry archive sync",
                }
            )
    return tuple(actions)


def _taxonomy_view(rows: tuple[Mapping[str, object], ...]) -> dict[str, tuple[str, ...]]:
    taxonomy: dict[str, list[str]] = {}
    for row in rows:
        taxonomy.setdefault(str(row["section"]), []).append(str(row["subcategory"]))
    return {section: tuple(subcategories) for section, subcategories in taxonomy.items()}


def _row_mapping(row: sqlite3.Row) -> dict[str, object]:
    return {key: row[key] for key in row.keys()}


def _require_allowed_table(table: str) -> None:
    if table not in TABLE_COLUMNS:
        raise OperationsConsoleError(f"unsupported console table: {table}")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
