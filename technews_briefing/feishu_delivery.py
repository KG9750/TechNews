"""Feishu delivery payload and status primitives."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Mapping

from .briefing_generation import GeneratedBriefing


class FeishuDeliveryError(ValueError):
    """Raised when Feishu delivery inputs are incomplete."""


RECEIVE_ID_TYPES = {"open_id", "chat_id"}
RECIPIENT_TYPES = {"feishu_user", "feishu_group"}
SENSITIVE_KEY_PARTS = ("authorization", "secret", "token", "tenant")
SENSITIVE_KEY_EXACT = {"receive_id", "open_id", "chat_id", "app_id", "sign"}
SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"Authorization\s*[:=]\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
    re.compile(r"\bou_[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\boc_[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bcli_[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"https://open\.(?:feishu|larksuite)\.cn/open-apis/bot/v2/hook/[A-Za-z0-9_-]+", re.IGNORECASE),
)


@dataclass(frozen=True)
class FeishuRecipient:
    recipient_key: str
    recipient_type: str
    receive_id_type: str
    receive_id: str
    path: str = "internal_app_bot"

    def __post_init__(self) -> None:
        if not self.recipient_key.strip():
            raise FeishuDeliveryError("recipient_key must be a non-empty string")
        if self.recipient_type not in RECIPIENT_TYPES:
            raise FeishuDeliveryError(f"recipient_type must be one of {sorted(RECIPIENT_TYPES)}")
        if self.receive_id_type not in RECEIVE_ID_TYPES:
            raise FeishuDeliveryError(f"receive_id_type must be one of {sorted(RECEIVE_ID_TYPES)}")
        if not self.receive_id.strip():
            raise FeishuDeliveryError("receive_id must be a non-empty string")
        if self.recipient_type == "feishu_user" and self.receive_id_type != "open_id":
            raise FeishuDeliveryError("feishu_user recipients must use receive_id_type open_id")
        if self.recipient_type == "feishu_group" and self.receive_id_type != "chat_id":
            raise FeishuDeliveryError("feishu_group recipients must use receive_id_type chat_id")


@dataclass(frozen=True)
class FeishuMessageRequest:
    recipient: FeishuRecipient
    method: str
    path: str
    query: Mapping[str, str]
    body: Mapping[str, object]
    content_format: str = "json_string"

    def as_evidence_shape(self) -> dict[str, object]:
        return {
            "path": self.recipient.path,
            "receive_id_type": self.recipient.receive_id_type,
            "body": redact_feishu_payload(dict(self.body)),
        }


def build_feishu_card(
    briefing: GeneratedBriefing,
    *,
    archive_url: str,
    title: str | None = None,
) -> dict[str, object]:
    if not archive_url.strip():
        raise FeishuDeliveryError("archive_url must be a non-empty string")

    elements: list[dict[str, object]] = []
    for group_index, group in enumerate(briefing.groups):
        if group_index:
            elements.append({"tag": "hr"})
        for item_index, item in enumerate(group.items):
            if item_index:
                elements.append({"tag": "hr"})
            detail = briefing.deep_dive_for_item(item.id)
            section_label = group.section if group.subcategory is None else f"{group.section} / {group.subcategory}"
            content_lines = [
                f"**{section_label}**",
                item.title_zh,
                *(f"- {bullet}" for bullet in item.bullets_zh),
            ]
            if item.confidence_notice is not None:
                content_lines.extend(
                    ["", f"**置信提示：**{_strip_confidence_prefix(item.confidence_notice.display_text_zh)}"]
                )
            content_lines.append(f"[Source]({item.original_source_anchor.source_url})")
            content_lines.append(f"[Deep-Dive]({_archive_url_for_detail(archive_url, detail.href)})")
            elements.append({"tag": "markdown", "content": "\n".join(content_lines)})

    elements.append(
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "Open Archive"},
                    "type": "default",
                    "url": archive_url,
                }
            ],
        }
    )
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": title or f"TechNews Briefing - {briefing.run_id}"},
        },
        "elements": elements,
    }


def build_internal_app_message_request(recipient: FeishuRecipient, card: Mapping[str, object]) -> FeishuMessageRequest:
    return FeishuMessageRequest(
        recipient=recipient,
        method="POST",
        path="/open-apis/im/v1/messages",
        query={"receive_id_type": recipient.receive_id_type},
        body={
            "receive_id": recipient.receive_id,
            "msg_type": "interactive",
            "content": json.dumps(card, ensure_ascii=False),
        },
    )


def render_feishu_message_text(briefing: GeneratedBriefing, *, archive_url: str) -> str:
    lines = [f"# TechNews Briefing - {briefing.run_id}", "", f"Archive: {archive_url}", ""]
    for group in briefing.groups:
        section_label = group.section if group.subcategory is None else f"{group.section} / {group.subcategory}"
        lines.extend([f"## {section_label}", ""])
        for item in group.items:
            detail = briefing.deep_dive_for_item(item.id)
            lines.extend([item.title_zh, ""])
            lines.extend(f"- {bullet}" for bullet in item.bullets_zh)
            if item.confidence_notice is not None:
                lines.extend(["", item.confidence_notice.display_text_zh])
            lines.extend(
                [
                    "",
                    f"Source: {item.original_source_anchor.source_url}",
                    f"Deep-Dive: {_archive_url_for_detail(archive_url, detail.href)}",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def delivery_status_from_response(recipient: FeishuRecipient, response: Mapping[str, object]) -> dict[str, object]:
    code = response.get("code")
    data = response.get("data")
    message_id = data.get("message_id") if isinstance(data, Mapping) else None
    base: dict[str, object] = {
        "recipient_type": recipient.recipient_type,
        "receive_id_type": recipient.receive_id_type,
        "path": recipient.path,
        "message_shape": "interactive_card",
    }
    if code == 0 and isinstance(message_id, str) and message_id.strip():
        return {
            **base,
            "status": "sent",
            "provider_message_id": message_id,
            "retryable": False,
        }
    return {
        **base,
        "status": "failed",
        "failure_reason": _failure_reason(response),
        "retryable": True,
        "provider_response": redact_feishu_payload(dict(response)),
    }


def build_delivery_status_map(
    responses_by_recipient: Mapping[FeishuRecipient, Mapping[str, object]],
) -> dict[str, dict[str, object]]:
    return {
        recipient.recipient_key: delivery_status_from_response(recipient, response)
        for recipient, response in responses_by_recipient.items()
    }


def pending_delivery_status(recipient: FeishuRecipient) -> dict[str, object]:
    return {
        "recipient_type": recipient.recipient_type,
        "receive_id_type": recipient.receive_id_type,
        "path": recipient.path,
        "status": "pending",
        "message_shape": "interactive_card",
        "retryable": True,
    }


def redact_feishu_payload(value):
    if isinstance(value, dict):
        redacted = {}
        for key, child in value.items():
            lowered = str(key).lower()
            if lowered in SENSITIVE_KEY_EXACT or any(part in lowered for part in SENSITIVE_KEY_PARTS):
                redacted[key] = "REDACTED"
            else:
                redacted[key] = redact_feishu_payload(child)
        return redacted
    if isinstance(value, list):
        return [redact_feishu_payload(item) for item in value]
    if isinstance(value, str):
        redacted = value
        for pattern in SENSITIVE_VALUE_PATTERNS:
            redacted = pattern.sub("REDACTED", redacted)
        return redacted
    return value


def _failure_reason(response: Mapping[str, object]) -> str:
    code = response.get("code", "unknown")
    message = response.get("msg") or response.get("message") or "Feishu delivery failed"
    return f"Feishu code {code}: {redact_feishu_payload(str(message))}"


def _strip_confidence_prefix(value: str) -> str:
    return value.removeprefix("置信提示：").strip()


def _archive_url_for_detail(archive_url: str, detail_href: str) -> str:
    if detail_href.startswith(("https://", "http://")):
        return detail_href
    return archive_url.rstrip("/") + "/" + detail_href.lstrip("/")
