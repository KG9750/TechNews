#!/usr/bin/env python3
"""Regression tests for the live daily briefing runner."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from technews_briefing.daily_run import FetchedMetadata, live_fetch_url, run_live_daily_briefing  # noqa: E402
from technews_briefing.source_registry import SourceRegistry  # noqa: E402


ENV_KEYS = [
    "FEISHU_APP_ID",
    "FEISHU_APP_SECRET",
    "FEISHU_DEFAULT_USER_OPEN_ID",
    "FEISHU_DEFAULT_CHAT_ID",
    "DELIVERY_DEADLINE_LOCAL_TIME",
    "DELIVERY_TIMEZONE",
    "MODEL_PROVIDER",
    "MODEL_DEFAULT_MODEL",
    "ARCHIVE_LOCAL_ROOT",
    "ARCHIVE_SYNC_TARGET",
    "ARCHIVE_PUBLIC_BASE_URL",
]


def with_env(values: Mapping[str, str]):
    class EnvGuard:
        def __enter__(self):
            self.old = {key: os.environ.get(key) for key in ENV_KEYS}
            for key, value in values.items():
                os.environ[key] = value
            return self

        def __exit__(self, exc_type, exc, tb):
            for key, value in self.old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    return EnvGuard()


def rss(title: str, link: str, pub_date: str, *, filler: str = "") -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0"><channel><title>Fixture Feed</title><item>
<title>{title}</title>
<link>{link}</link>
<pubDate>{pub_date}</pubDate>
<description>Short metadata-only description.{filler}</description>
</item></channel></rss>
"""


def atom(title: str, url: str, published: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>Fixture arXiv Feed</title>
<entry>
<title>{title}</title>
<id>{url}</id>
<link href="{url}" rel="alternate" />
<published>{published}</published>
<summary>Short metadata-only abstract for live runner tests.</summary>
<author><name>Fixture Author</name></author>
<category term="cs.AI" />
</entry>
</feed>
"""


def test_arxiv_live_url_adds_single_result_limit() -> None:
    registry = SourceRegistry.from_markdown_file(ROOT / "docs/source-registry.md")
    source = registry.entry_for("src-arxiv-cs-ai")
    url = live_fetch_url(source)
    assert "max_results=1" in url
    assert "sortBy=submittedDate" in url


def test_daily_runner_fetches_live_metadata_and_delivers_non_fixture_card() -> None:
    sent_requests: list[tuple[str, Mapping[str, object], Mapping[str, str]]] = []
    seen_fetch_urls: dict[str, str] = {}

    def fake_fetch(source, fetch_url: str, max_feed_bytes: int) -> FetchedMetadata:
        seen_fetch_urls[source.id] = fetch_url
        if source.id == "src-kubernetes-blog":
            content = rss(
                "Kubernetes Live Metadata Test",
                "https://kubernetes.io/blog/2026/06/08/live-metadata-test/",
                "Mon, 08 Jun 2026 00:15:00 GMT",
                filler="<description>" + ("x" * 1_100_000) + "</description>",
            )
        elif source.source_type == "public_feed":
            content = rss(
                f"{source.name} Live Metadata Test",
                f"https://example.invalid/{source.id}/live-metadata-test",
                "Mon, 08 Jun 2026 00:10:00 GMT",
            )
        else:
            content = atom(
                f"{source.name} Live Paper Test",
                f"https://arxiv.org/abs/2606.{len(seen_fetch_urls):05d}v1",
                "2026-06-08T00:20:00Z",
            )
        return FetchedMetadata(
            content=content,
            content_type="application/xml",
            final_url=fetch_url,
            http_status=200,
            byte_count=len(content.encode("utf-8")),
            elapsed_ms=1,
        )

    def fake_send_json(url: str, payload: Mapping[str, object], headers: Mapping[str, str]) -> Mapping[str, object]:
        sent_requests.append((url, payload, headers))
        if url.endswith("/open-apis/auth/v3/tenant_access_token/internal"):
            return {"code": 0, "tenant_access_token": "tenant-token-for-test"}
        return {"code": 0, "data": {"message_id": f"om_fixture_{len(sent_requests)}"}}

    with tempfile.TemporaryDirectory(dir=ROOT) as tmp_name:
        tmp = Path(tmp_name)
        with with_env(
            {
                "FEISHU_APP_ID": "cli_fixture_app_id",
                "FEISHU_APP_SECRET": "fixture-secret",
                "FEISHU_DEFAULT_USER_OPEN_ID": "ou_fixture_user",
                "FEISHU_DEFAULT_CHAT_ID": "oc_fixture_group",
                "DELIVERY_DEADLINE_LOCAL_TIME": "08:00",
                "DELIVERY_TIMEZONE": "Asia/Shanghai",
                "MODEL_PROVIDER": "deterministic",
                "MODEL_DEFAULT_MODEL": "none",
                "ARCHIVE_LOCAL_ROOT": str(tmp / "archives"),
                "ARCHIVE_SYNC_TARGET": str(tmp / "sync"),
                "ARCHIVE_PUBLIC_BASE_URL": "https://archive.example.invalid",
            }
        ):
            result = run_live_daily_briefing(
                repo_root=ROOT,
                now=datetime(2026, 6, 8, 0, 30, tzinfo=timezone.utc),
                deliver=True,
                write_report=True,
                report_path=tmp / "report.redacted.json",
                fetch=fake_fetch,
                send_json=fake_send_json,
                arxiv_delay_seconds=0,
            )
            report_exists = bool(result.report_path and result.report_path.exists())

    serialized_report = json.dumps(result.report, ensure_ascii=False)
    sent_payloads = json.dumps([payload for _, payload, _ in sent_requests], ensure_ascii=False)

    assert len(result.run.accepted_candidates) == 7
    assert result.delivered is True
    assert result.archive.metadata.sync_status["remote_sync"].status == "synced"
    assert report_exists
    assert "TechNews Briefing - 2026-06-01" not in sent_payloads
    assert "GPT-4o" not in sent_payloads
    assert "Kubernetes Live Metadata Test" in sent_payloads
    assert "https://archive.example.invalid/2026-06-08/technology/deep-dive/" in sent_payloads
    assert "max_results=1" in seen_fetch_urls["src-arxiv-cs-ai"]
    assert "ou_fixture_user" not in serialized_report
    assert "oc_fixture_group" not in serialized_report
    assert str(ROOT) not in serialized_report


def main() -> int:
    test_arxiv_live_url_adds_single_result_limit()
    test_daily_runner_fetches_live_metadata_and_delivers_non_fixture_card()
    print("daily run tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
