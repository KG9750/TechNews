# Use single-administrator password access for the Operations Console

Status: accepted

The MVP Operations Console will use one Briefing Administrator account protected by username, password hash, and signed session secret. This is enough for first-version setup and operations because the console is not a consumer reading app and does not need team permissions, social login, or per-user audit trails yet.

OAuth, SSO, and multi-account role management are deferred. They add configuration and security surface area before the MVP has more than one administrator or a need for organization-wide access control.

**Tradeoffs**

- Single-admin access is simple to deploy on a private Briefing Host, but it does not support delegated operations.
- Password sessions avoid third-party auth setup, but require careful secret handling and password-hash storage.
- Keeping the console private by default is appropriate for MVP, but remote access later may require stronger auth and network controls.

**Consequences**

- The first console implementation should use `ADMIN_USERNAME`, `ADMIN_PASSWORD_HASH`, and `SESSION_SECRET`.
- Plaintext admin passwords must never be committed or logged.
- The console should expose configuration, run status, retry controls, and archive links, not a full public reading experience.
- Multi-user roles are a post-MVP feature unless the administrator access requirement changes before implementation.
