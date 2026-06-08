"""Live metadata-only daily briefing runner."""

from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass
from datetime import date, datetime, time as time_of_day, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .archive_package import ArchivePackageResult, write_archive_package
from .briefing_generation import GeneratedBriefing, generate_briefing
from .feishu_delivery import (
    FeishuMessageRequest,
    FeishuRecipient,
    build_delivery_status_map,
    build_feishu_card,
    build_internal_app_message_request,
    pending_delivery_status,
    redact_feishu_payload,
    render_feishu_message_text,
)
from .ranking import RankingInput, RankingResult, rank_candidates
from .run import AutomaticBriefingRun, ConnectorResult, RunPreparation
from .source_connectors import SourceMetadataInput, run_source_connectors
from .source_policy import SourceAccessPolicy
from .source_registry import SourceRegistry, SourceRegistryEntry


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = ROOT / "fixtures/source-ingestion/source-access-policy.json"
DEFAULT_REGISTRY_PATH = ROOT / "docs/source-registry.md"
DEFAULT_REPORT_PATH = ROOT / "evidence/daily-run/latest-report.redacted.json"
FEISHU_BASE_URL = "https://open.feishu.cn"
USER_AGENT = "TechNewsBriefing/0.1 metadata-only live daily runner"


class DailyRunError(ValueError):
    """Raised when the live daily run cannot proceed safely."""


@dataclass(frozen=True)
class RetentionResult:
    env_name: str
    status: str
    date_dirs_scanned: int
    removed: int
    non_date_dirs_skipped: int

    def as_mapping(self) -> dict[str, object]:
        return {
            "env_name": self.env_name,
            "status": self.status,
            "date_dirs_scanned": self.date_dirs_scanned,
            "removed": self.removed,
            "non_date_dirs_skipped": self.non_date_dirs_skipped,
        }


@dataclass(frozen=True)
class FetchedMetadata:
    content: str
    content_type: str
    final_url: str
    http_status: int
    byte_count: int
    elapsed_ms: int


@dataclass(frozen=True)
class FetchReport:
    source_id: str
    source_name: str
    status: str
    http_status: int | None = None
    content_type: str | None = None
    byte_count: int = 0
    elapsed_ms: int = 0
    error_type: str | None = None

    def as_mapping(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "status": self.status,
            "byte_count": self.byte_count,
            "elapsed_ms": self.elapsed_ms,
        }
        if self.http_status is not None:
            payload["http_status"] = self.http_status
        if self.content_type is not None:
            payload["content_type"] = self.content_type
        if self.error_type is not None:
            payload["error_type"] = self.error_type
        return payload


@dataclass(frozen=True)
class DailyRunResult:
    run: RunPreparation
    ranking: RankingResult
    briefing: GeneratedBriefing
    archive: ArchivePackageResult
    feishu_requests: tuple[FeishuMessageRequest, ...]
    delivery_status: Mapping[str, Mapping[str, object]]
    fetch_reports: tuple[FetchReport, ...]
    retention: tuple[RetentionResult, ...]
    report: Mapping[str, object]
    report_path: Path | None = None

    @property
    def delivered(self) -> bool:
        return bool(self.delivery_status) and all(
            status.get("status") == "sent" for status in self.delivery_status.values()
        )


FetchFunction = Callable[[SourceRegistryEntry, str, int], FetchedMetadata]
SendJsonFunction = Callable[[str, Mapping[str, object], Mapping[str, str]], Mapping[str, object]]


def load_env_file(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def run_live_daily_briefing(
    *,
    repo_root: Path = ROOT,
    now: datetime | None = None,
    deliver: bool = True,
    write_report: bool = True,
    report_path: Path = DEFAULT_REPORT_PATH,
    fetch: FetchFunction | None = None,
    send_json: SendJsonFunction | None = None,
    max_feed_bytes: int = 6_000_000,
    arxiv_delay_seconds: float = 3.0,
) -> DailyRunResult:
    load_env_file(repo_root / ".env")
    started = _utc_now(now)
    schedule = _schedule_for(started)
    run_id = "run_" + schedule["local_date"].replace("-", "") + "_daily_live"

    registry = SourceRegistry.from_markdown_file(repo_root / "docs/source-registry.md")
    policy = SourceAccessPolicy.from_file(repo_root / "fixtures/source-ingestion/source-access-policy.json")
    sources = registry.production_enabled_connectors(policy)
    if not sources:
        raise DailyRunError("no production-enabled source connectors are configured")

    retention = enforce_archive_retention(today=schedule["local_date_obj"])
    source_inputs, fetch_reports = fetch_live_source_inputs(
        sources,
        fetch=fetch or fetch_source_metadata,
        now=started,
        max_feed_bytes=max_feed_bytes,
        arxiv_delay_seconds=arxiv_delay_seconds,
    )
    connector_results = run_source_connectors(
        registry,
        policy,
        source_inputs,
        run_id=run_id,
        discovered_at=_iso_utc(started),
        delivery_deadline=schedule["delivery_deadline"],
    )
    preparation = AutomaticBriefingRun(policy).prepare(
        run_id=run_id,
        domain_template="technology",
        scheduled_for=schedule["scheduled_for"],
        delivery_deadline=schedule["delivery_deadline"],
        started_at=_iso_utc(started),
        connector_results=connector_results,
    )
    if not preparation.accepted_candidates:
        raise DailyRunError("live fetch produced no accepted candidates")

    ranking = rank_candidates(
        build_ranking_inputs(preparation.accepted_candidates, registry),
        subscribed_sections={"AI", "Academic Progress", "Software", "Embodied Intelligence", "Hardware"},
        run_started_at=_iso_utc(started),
        max_selected=8,
    )
    if not ranking.selected:
        raise DailyRunError("ranking selected no candidates")

    briefing = generate_briefing(ranking.selected, run_id=run_id)
    archive_url = archive_url_for(schedule["generated_at"])
    delivery_status, feishu_requests = deliver_briefing(
        briefing,
        archive_url=archive_url,
        deliver=deliver,
        send_json=send_json or request_json,
    )
    archive = write_archive_package(
        briefing,
        local_root=_required_path_env("ARCHIVE_LOCAL_ROOT"),
        generated_at=schedule["generated_at"],
        domain_template="technology",
        excluded_candidates=ranking.archive_excluded_candidates(),
        connector_status=connector_status_map(connector_results),
        delivery_status=delivery_status,
        model_usage_summary={
            "provider": os.environ.get("MODEL_PROVIDER", "not_called"),
            "model": os.environ.get("MODEL_DEFAULT_MODEL", "not_called"),
            "task_count": 0,
            "request_count": 0,
            "failure_count": 0,
            "notes": "Live daily runner used deterministic ranking/generation; no model provider call was made.",
        },
        sync_target=_optional_path_env("ARCHIVE_SYNC_TARGET"),
        sync_attempted_at=schedule["generated_at"],
        warnings=tuple(preparation.run.run_warnings),
    )

    report = build_redacted_report(
        run_id=run_id,
        schedule=schedule,
        fetch_reports=fetch_reports,
        connector_results=connector_results,
        selected_titles=[selected.candidate.original_title for selected in ranking.selected],
        archive=archive,
        delivery_status=delivery_status,
        retention=retention,
        rendered_message=render_feishu_message_text(briefing, archive_url=archive_url),
    )
    resolved_report_path = report_path if write_report else None
    if resolved_report_path is not None:
        resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return DailyRunResult(
        run=preparation,
        ranking=ranking,
        briefing=briefing,
        archive=archive,
        feishu_requests=feishu_requests,
        delivery_status=delivery_status,
        fetch_reports=fetch_reports,
        retention=retention,
        report=report,
        report_path=resolved_report_path,
    )


def enforce_archive_retention(*, today: date | None = None, days: int = 7) -> tuple[RetentionResult, ...]:
    cutoff = (today or date.today()) - timedelta(days=days)
    results = []
    for env_name in ("ARCHIVE_LOCAL_ROOT", "ARCHIVE_SYNC_TARGET"):
        raw = os.environ.get(env_name, "")
        if not raw:
            results.append(RetentionResult(env_name, "missing", 0, 0, 0))
            continue
        root = Path(raw).expanduser()
        if not root.exists():
            results.append(RetentionResult(env_name, "missing_path", 0, 0, 0))
            continue
        scanned = removed = skipped = 0
        for child in root.iterdir():
            if not child.is_dir():
                continue
            try:
                child_date = datetime.strptime(child.name, "%Y-%m-%d").date()
            except ValueError:
                skipped += 1
                continue
            scanned += 1
            if child_date < cutoff:
                shutil.rmtree(child)
                removed += 1
        results.append(RetentionResult(env_name, "ok", scanned, removed, skipped))
    return tuple(results)


def fetch_live_source_inputs(
    sources: tuple[SourceRegistryEntry, ...],
    *,
    fetch: FetchFunction,
    now: datetime,
    max_feed_bytes: int,
    arxiv_delay_seconds: float,
) -> tuple[tuple[SourceMetadataInput, ...], tuple[FetchReport, ...]]:
    inputs: list[SourceMetadataInput] = []
    reports: list[FetchReport] = []
    for index, source in enumerate(sources):
        fetch_url = live_fetch_url(source)
        if index and _is_arxiv_url(fetch_url) and arxiv_delay_seconds:
            time.sleep(arxiv_delay_seconds)
        try:
            fetched = fetch(source, fetch_url, max_feed_bytes)
            inputs.append(
                SourceMetadataInput(
                    source_id=source.id,
                    content=fetched.content,
                    content_type=fetched.content_type,
                    fetched_url=fetched.final_url,
                )
            )
            reports.append(
                FetchReport(
                    source_id=source.id,
                    source_name=source.name,
                    status="fetched",
                    http_status=fetched.http_status,
                    content_type=fetched.content_type,
                    byte_count=fetched.byte_count,
                    elapsed_ms=fetched.elapsed_ms,
                )
            )
        except (HTTPError, URLError, TimeoutError, OSError, DailyRunError) as error:
            inputs.append(
                SourceMetadataInput(
                    source_id=source.id,
                    error=f"live fetch failed: {type(error).__name__}",
                )
            )
            reports.append(
                FetchReport(
                    source_id=source.id,
                    source_name=source.name,
                    status="fetch_failed",
                    error_type=type(error).__name__,
                )
            )
    return tuple(inputs), tuple(reports)


def fetch_source_metadata(source: SourceRegistryEntry, fetch_url: str, max_feed_bytes: int) -> FetchedMetadata:
    started = time.time()
    request = Request(
        fetch_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        },
    )
    with urlopen(request, timeout=30) as response:
        body = response.read(max_feed_bytes + 1)
        if len(body) > max_feed_bytes:
            raise DailyRunError(f"{source.id} feed exceeds metadata fetch byte limit")
        content_type = response.headers.get("Content-Type", "application/octet-stream").split(";", 1)[0]
        status = int(getattr(response, "status", 200))
        final_url = response.geturl()
    return FetchedMetadata(
        content=body.decode("utf-8", errors="replace"),
        content_type=content_type,
        final_url=final_url,
        http_status=status,
        byte_count=len(body),
        elapsed_ms=int((time.time() - started) * 1000),
    )


def live_fetch_url(source: SourceRegistryEntry) -> str:
    if not _is_arxiv_url(source.url_or_feed):
        return source.url_or_feed
    parsed = urlparse(source.url_or_feed)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("max_results", "1")
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(query), parsed.fragment))


def build_ranking_inputs(
    candidates: tuple,
    registry: SourceRegistry,
) -> tuple[RankingInput, ...]:
    inputs: list[RankingInput] = []
    for candidate in candidates:
        source = registry.entry_for(candidate.source_id)
        section = candidate.section_hints[0] if candidate.section_hints else source.primary_section
        subcategory = candidate.section_hints[1] if len(candidate.section_hints) > 1 else None
        confidence_level = "high" if candidate.published_at else "medium"
        confidence_notice = None
        if confidence_level != "high":
            confidence_notice = "该条目缺少可核验发布时间，当前仅按来源元数据进入候选池。"
        inputs.append(
            RankingInput(
                candidate=candidate,
                section=section,
                subcategory=subcategory,
                source_trust=source.trust_tier,
                event_impact=_event_impact(source, candidate.published_at),
                confidence_level=confidence_level,
                confidence_notice=confidence_notice,
                original_material_available=True,
            )
        )
    return tuple(inputs)


def connector_status_map(connector_results: tuple[ConnectorResult, ...]) -> dict[str, dict[str, object]]:
    statuses: dict[str, dict[str, object]] = {}
    for result in connector_results:
        payload: dict[str, object] = {
            "status": result.status,
            "item_count": len(result.candidates),
        }
        if result.warning:
            payload["warning"] = result.warning
        statuses[result.source_id] = payload
    return statuses


def deliver_briefing(
    briefing: GeneratedBriefing,
    *,
    archive_url: str,
    deliver: bool,
    send_json: SendJsonFunction,
) -> tuple[dict[str, dict[str, object]], tuple[FeishuMessageRequest, ...]]:
    recipients = configured_feishu_recipients()
    card = build_feishu_card(briefing, archive_url=archive_url)
    requests = tuple(build_internal_app_message_request(recipient, card) for recipient in recipients)
    if not deliver:
        return ({recipient.recipient_key: pending_delivery_status(recipient) for recipient in recipients}, requests)
    if not recipients:
        return ({}, requests)

    token = tenant_access_token(send_json)
    responses = {}
    for request in requests:
        url = f"{FEISHU_BASE_URL}{request.path}?{urlencode(request.query)}"
        response = send_json(
            url,
            request.body,
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        responses[request.recipient] = response
    return build_delivery_status_map(responses), requests


def configured_feishu_recipients() -> tuple[FeishuRecipient, ...]:
    recipients = []
    user_open_id = os.environ.get("FEISHU_DEFAULT_USER_OPEN_ID", "")
    chat_id = os.environ.get("FEISHU_DEFAULT_CHAT_ID", "")
    if user_open_id:
        recipients.append(
            FeishuRecipient(
                recipient_key="default_user",
                recipient_type="feishu_user",
                receive_id_type="open_id",
                receive_id=user_open_id,
            )
        )
    if chat_id:
        recipients.append(
            FeishuRecipient(
                recipient_key="default_group",
                recipient_type="feishu_group",
                receive_id_type="chat_id",
                receive_id=chat_id,
            )
        )
    return tuple(recipients)


def tenant_access_token(send_json: SendJsonFunction) -> str:
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        raise DailyRunError("FEISHU_APP_ID and FEISHU_APP_SECRET are required for live delivery")
    response = send_json(
        f"{FEISHU_BASE_URL}/open-apis/auth/v3/tenant_access_token/internal",
        {"app_id": app_id, "app_secret": app_secret},
        {"Content-Type": "application/json"},
    )
    token = response.get("tenant_access_token")
    if not isinstance(token, str) or not token.strip():
        raise DailyRunError("tenant token request failed")
    return token


def request_json(url: str, payload: Mapping[str, object], headers: Mapping[str, str]) -> Mapping[str, object]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=body, headers=dict(headers), method="POST")
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        text = error.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = {"raw": text}
        parsed["_http_status"] = error.code
        return parsed


def archive_url_for(generated_at: str) -> str:
    relative = f"{generated_at[:10]}/technology/"
    base = os.environ.get("ARCHIVE_PUBLIC_BASE_URL", "").strip()
    if base:
        return base.rstrip("/") + "/" + relative
    sync_target = os.environ.get("ARCHIVE_SYNC_TARGET", "").strip()
    if sync_target.startswith(("https://", "http://")):
        return sync_target.rstrip("/") + "/" + relative
    return "https://archive.local.invalid/" + relative


def build_redacted_report(
    *,
    run_id: str,
    schedule: Mapping[str, object],
    fetch_reports: tuple[FetchReport, ...],
    connector_results: tuple[ConnectorResult, ...],
    selected_titles: list[str],
    archive: ArchivePackageResult,
    delivery_status: Mapping[str, Mapping[str, object]],
    retention: tuple[RetentionResult, ...],
    rendered_message: str,
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "generated_at": schedule["generated_at"],
        "delivery_deadline": schedule["delivery_deadline"],
        "fetch": [report.as_mapping() for report in fetch_reports],
        "connectors": connector_status_map(connector_results),
        "selected_count": len(selected_titles),
        "selected_titles": selected_titles,
        "archive": {
            "local_status": archive.metadata.sync_status["local_archive"].status,
            "remote_status": archive.metadata.sync_status["remote_sync"].status,
            "file_count": len(archive.files_written),
        },
        "delivery": redact_feishu_payload({key: dict(value) for key, value in delivery_status.items()}),
        "retention": [item.as_mapping() for item in retention],
        "rendered_message_preview": rendered_message[:1200],
    }


def _schedule_for(now: datetime) -> dict[str, object]:
    timezone_name = os.environ.get("DELIVERY_TIMEZONE", "Asia/Shanghai")
    deadline_text = os.environ.get("DELIVERY_DEADLINE_LOCAL_TIME", "08:00")
    hour_text, minute_text = deadline_text.split(":", 1)
    local_tz = ZoneInfo(timezone_name)
    local_now = now.astimezone(local_tz)
    local_date = local_now.date()
    local_deadline = datetime.combine(
        local_date,
        time_of_day(hour=int(hour_text), minute=int(minute_text)),
        tzinfo=local_tz,
    )
    deadline_utc = local_deadline.astimezone(timezone.utc)
    return {
        "local_date": local_date.isoformat(),
        "local_date_obj": local_date,
        "scheduled_for": _iso_utc(deadline_utc),
        "delivery_deadline": _iso_utc(deadline_utc),
        "generated_at": _iso_utc(now),
    }


def _required_path_env(name: str) -> Path:
    value = os.environ.get(name, "")
    if not value:
        raise DailyRunError(f"{name} is required")
    return Path(value).expanduser()


def _optional_path_env(name: str) -> Path | None:
    value = os.environ.get(name, "")
    return Path(value).expanduser() if value else None


def _event_impact(source: SourceRegistryEntry, published_at: str | None) -> int:
    if source.trust_tier == "official":
        return 4
    if source.trust_tier == "academic":
        return 3
    if published_at:
        return 3
    return 2


def _utc_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_arxiv_url(url: str) -> bool:
    return "export.arxiv.org" in urlparse(url).netloc
