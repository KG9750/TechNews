# Feishu Delivery Fixtures

Status: Message fixture only; live delivery pending
Last updated: 2026-06-01

These fixtures prepare the Feishu delivery spike without storing secrets or recipient identifiers.

Contents:

- `rendered-message.md`: copied-text representation of the Push Briefing that should appear in Feishu.
- `push-briefing-card-content.json`: draft message-card content object for an internal app bot.
- `internal-app-send-message.request-shape.json`: redacted request shape with user and group placeholders.
- `delivery-status-examples.json`: success and failure status shapes for Archive Metadata and run state.

The fixture does not prove Feishu delivery. A real spike must use `FEISHU_APP_ID`, `FEISHU_APP_SECRET`, `FEISHU_DEFAULT_USER_OPEN_ID`, and `FEISHU_DEFAULT_CHAT_ID`, then attach redacted request/response evidence.
