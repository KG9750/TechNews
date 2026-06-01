# Briefing Style Guide

Status: Draft
Last updated: 2026-06-01

This guide defines the writing style for Push Briefings and Deep-Dive Details.

## Push Briefing Item

Each item must include:

- One Chinese title sentence.
- Three to four concise Chinese bullets.
- Original Source Anchor.
- Confidence level.
- Confidence Notice when confidence is medium or low.
- Media attribution when source media is used.

## Title Rules

Use:

- One sentence.
- Concrete subject and outcome.
- No hype.
- No unsupported causal claims.

Avoid:

- "震撼发布", "颠覆行业", "史诗级" and similar sensational wording.
- Titles that hide the actor.
- Titles that imply certainty when the item has a Confidence Notice.

Accepted example:

```text
OpenAI 发布新一代多模态模型，重点降低实时语音和视觉交互门槛。
```

Rejected example:

```text
OpenAI 彻底改变 AI 行业格局。
```

## Bullet Rules

Use three to four bullets:

- Bullet 1: what happened.
- Bullet 2: why it matters.
- Bullet 3: evidence or source context.
- Bullet 4: optional caveat, follow-up, or related history.

Keep bullets short enough for Feishu scanning. Do not copy long source passages.

## Confidence Notice Rules

Add a Confidence Notice when:

- Only one weak source is available.
- Sources disagree.
- The item is a rumor, leak, or unconfirmed report.
- Important metadata is missing.
- The model had to infer context from limited evidence.

Accepted example:

```text
置信提示：目前只有单一来源报道，尚未看到公司公告或多家媒体交叉确认。
```

Rejected example:

```text
可能是真的。
```

## Source And Media Attribution

- Always show source name, original title, and source URL.
- Use only Source Media from the original source, official entity page, paper page, or structured site metadata.
- If media rights are unclear, omit media or use a neutral structured fallback.
- Never generate news imagery with AI for MVP briefings.

## Deep-Dive Detail

Deep-Dive Detail may include:

- Richer summary.
- Source list.
- Selection Rationale.
- Confidence Notice.
- Related History.
- Candidate metadata.
- Media attribution.

It must not include AI chat in the MVP.
