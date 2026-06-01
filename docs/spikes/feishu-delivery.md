# Feishu Delivery Spike

Status: Not started
Owner: Briefing Administrator

## Decision To Prove

Use a Feishu internal app bot as the primary MVP delivery path for both users and groups. Keep a custom group bot only as a group-chat fallback.

## Inputs

- Minimal contracts: `docs/schemas/minimal-contracts.md`
- Secrets inventory: `docs/secrets.md`
- Proposed ADR: `docs/adr/0002-feishu-internal-app-bot-first.md`

## Test Message Shape

The test Push Briefing must include:

- Date and domain template.
- Two Briefing Sections.
- At least one high-confidence item.
- At least one item with a Confidence Notice.
- At least one Original Source Anchor.
- A link placeholder for an Archived Briefing or Deep-Dive Detail.

## Questions To Answer

- Which Feishu API endpoint and card format should MVP use?
- Which recipient identifiers should be stored for users and groups?
- Which app scopes and bot installation steps are required?
- What rate limits and message-size limits affect daily delivery?
- What failure payload should be stored in `delivery_status`?
- Can a group webhook fallback represent enough delivery status for MVP?

## Verification Checklist

- Internal app bot sends the test Push Briefing to one real Feishu user.
- Internal app bot sends the test Push Briefing to one real Feishu group.
- Message includes section headers, source link, and confidence notice.
- Recipient ids, scopes, permissions, and failure responses are documented.
- ADR-0002 is either accepted or superseded.

## Evidence To Attach

- Redacted request payload.
- Redacted success response for user delivery.
- Redacted success response for group delivery.
- Screenshot or copied rendered-message text.
- Failure response examples if available.

## Official References

- Feishu send message API: https://open.feishu.cn/document/server-docs/im-v1/message/create?lang=zh-CN
- Feishu card sending guide: https://open.feishu.cn/document/feishu-cards/send-feishu-card
- Message card OpenAPI reference: https://open.larksuite.com/document/common-capabilities/message-card/api-and-resource-reference
