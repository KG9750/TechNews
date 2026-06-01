# Prefer Feishu internal app bot for MVP delivery

Status: proposed

The MVP requires push delivery to both Feishu users and Feishu groups. The default delivery path is a Feishu internal app bot because it is the most likely path to support both recipient types with auditable permissions, recipient identifiers, and card messages. A custom group bot remains a fallback for group-chat delivery only and must not replace the internal app bot unless the Feishu delivery spike proves personal delivery is unnecessary or unsupported.

**Tradeoffs**

- An internal app bot requires app setup, scopes, and recipient identifiers, but it can support both personal and group delivery.
- A custom group bot is simpler to configure for one chat, but it does not satisfy the MVP requirement for personal delivery.
- Keeping the group bot as fallback preserves an escape path for group pushes without making it the primary architecture.

**Consequences**

- The Feishu delivery spike must validate one real user and one real group.
- Recipient storage must support user identifiers and group chat identifiers.
- MVP implementation issues must not be marked `ready-for-agent` until this ADR is accepted or replaced.
