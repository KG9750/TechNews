# Feishu Delivery Spike

Status: Message fixture ready; live user and group delivery pending
Owner: Briefing Administrator

## Decision To Prove

Use a Feishu internal app bot as the primary MVP delivery path for both users and groups. Keep a custom group bot only as a group-chat fallback.

## Inputs

- Minimal contracts: `docs/schemas/minimal-contracts.md`
- Secrets inventory: `docs/secrets.md`
- Proposed ADR: `docs/adr/0002-feishu-internal-app-bot-first.md`
- Rendered message fixture: `fixtures/feishu-delivery/rendered-message.md`
- Draft card content fixture: `fixtures/feishu-delivery/push-briefing-card-content.json`
- Draft internal app request shape: `fixtures/feishu-delivery/internal-app-send-message.request-shape.json`
- Delivery status examples: `fixtures/feishu-delivery/delivery-status-examples.json`
- Throwaway live runner: `scripts/spikes/feishu_delivery_spike.py`

## Test Message Shape

The test Push Briefing must include:

- Date and domain template.
- Two Briefing Sections.
- At least one high-confidence item.
- At least one item with a Confidence Notice.
- At least one Original Source Anchor.
- A link placeholder for an Archived Briefing or Deep-Dive Detail.

## Questions To Answer

- Which Feishu API endpoint and card format should MVP use? Current fixture assumes internal app bot `im/v1/messages` with an interactive card and must be validated live.
- Which recipient identifiers should be stored for users and groups?
- Which app scopes and bot installation steps are required?
- What rate limits and message-size limits affect daily delivery?
- What failure payload should be stored in `delivery_status`?
- Can a group webhook fallback represent enough delivery status for MVP?

## Verification Checklist

- [ ] Internal app bot sends the test Push Briefing to one real Feishu user.
- [ ] Internal app bot sends the test Push Briefing to one real Feishu group.
- [x] Message fixture includes section headers, source link, and confidence notice.
- [ ] Recipient ids, scopes, permissions, and failure responses are documented from live setup.
- [ ] ADR-0002 is either accepted or superseded.

## Evidence To Attach

- Draft request payload: `fixtures/feishu-delivery/internal-app-send-message.request-shape.json`.
- Draft rendered-message text: `fixtures/feishu-delivery/rendered-message.md`.
- Draft delivery status examples: `fixtures/feishu-delivery/delivery-status-examples.json`.
- Dry-run command: `python3 scripts/spikes/feishu_delivery_spike.py --dry-run`.
- Live command: `python3 scripts/spikes/feishu_delivery_spike.py`.
- Pending: redacted success response for user delivery.
- Pending: redacted success response for group delivery.
- Pending: screenshot or copied rendered-message text from Feishu.
- Pending: real failure response examples if available.

## Current Finding

The message shape is ready for a live internal app bot test. The fixture covers two sections, a source link, a Confidence Notice, and an archive/deep-dive link placeholder. The spike is not complete until real Feishu credentials, one user recipient id, and one group chat id are available and both sends are proven.

## Official References

- Feishu send message API: https://open.feishu.cn/document/server-docs/im-v1/message/create?lang=zh-CN
- Feishu card sending guide: https://open.feishu.cn/document/feishu-cards/send-feishu-card
- Message card OpenAPI reference: https://open.larksuite.com/document/common-capabilities/message-card/api-and-resource-reference
