# Briefing Style Guide

Status: Reviewed for model spike
Last updated: 2026-06-03

This guide defines the writing style for Push Briefings and Deep-Dive Details. It is the canonical writing reference for the Model Provider Spike.

## Push Briefing Structure

Each Push Briefing item must include:

- One Chinese title sentence.
- Three to four concise Chinese bullets.
- Briefing Section and optional Section Subcategory.
- Original Source Anchor.
- Confidence level.
- Confidence Notice when confidence is `medium` or `low`.
- Media attribution when Source Media is displayed.

Preferred item order:

1. Title.
2. Section and subcategory.
3. Bullets.
4. Confidence Notice, when required.
5. Source line.
6. Media attribution, when required.

## Title Rules

Use:

- One sentence.
- Concrete actor, action, and outcome.
- Neutral language.
- A caveat in the title only when uncertainty materially changes interpretation.

Avoid:

- "震撼发布", "颠覆行业", "史诗级", "炸裂", "杀疯了" and similar sensational wording.
- Unsupported causal claims.
- Titles that hide the actor.
- Titles that imply certainty when the item has a Confidence Notice.

Accepted:

```text
OpenAI 发布 GPT-4o，重点降低实时多模态交互门槛。
```

Rejected:

```text
OpenAI 彻底改变 AI 行业格局。
```

## Bullet Rules

Use three to four bullets:

- Bullet 1: what happened.
- Bullet 2: why it matters.
- Bullet 3: evidence, source context, or original-material anchor.
- Bullet 4: optional caveat, related history, or next thing to watch.

Rules:

- Each bullet should be one sentence.
- Keep each bullet compact enough for Feishu scanning.
- Do not copy long source passages.
- Do not mention missing information unless it changes interpretation.
- Do not include raw URLs inside bullets when a source line is available.

Accepted:

```text
- 这是一次官方模型发布，覆盖文本、语音和视觉交互。
- 影响点在于实时交互成本和产品形态，而不是单一 benchmark。
- 原始来源为 OpenAI 官方公告，适合作为高置信条目处理。
```

Rejected:

```text
- 这篇文章说了很多，包括模型、语音、视觉、API、产品、未来计划，大家都应该关注。
```

## Confidence Notice Rules

Add a Confidence Notice when:

- Only one weak source is available.
- Sources disagree.
- The item is a rumor, leak, or unconfirmed report.
- Important metadata is missing.
- Source access failed and fallback metadata was used.
- The model had to infer context from limited evidence.

Use this shape:

```text
置信提示：<uncertainty reason>；当前依据为 <supporting source summary>。
```

Accepted:

```text
置信提示：目前只有单一来源报道，尚未看到公司公告或多家媒体交叉确认；当前依据为手动添加链接的页面 metadata。
```

Rejected:

```text
可能是真的。
```

## Source And Media Attribution

Always preserve:

- Source name.
- Original title.
- Source URL.

Source line shape:

```text
来源：<source_name> - <original_title>
```

Media rules:

- Use only Source Media from the original source, official entity page, paper page, or structured site metadata.
- Show Media Attribution whenever media is displayed.
- If media rights are unclear, omit media or use a neutral structured fallback.
- Never generate news imagery with AI for MVP briefings.

Accepted media attribution:

```text
图片来源：Apple Newsroom / Open Graph metadata
```

Rejected media attribution:

```text
配图：AI 生成，仅供参考
```

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

## Quality Checklist

Before accepting generated output, verify:

- Title is one sentence and not sensational.
- Bullets have three or four items.
- Original Source Anchor is present.
- Medium and low confidence items include a Confidence Notice.
- Source Media is not invented.
- Media Attribution exists when media is displayed.
- Summary does not store or reproduce long article body text.
- Section and subcategory names match `docs/taxonomy/technology-domain-template.md`.
- `python3 scripts/check_readiness.py` verifies the required Push Briefing, Confidence Notice, Source/Media, Deep-Dive Detail, and quality checklist rules.
