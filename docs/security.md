# Security & Threat Model

## STRIDE Threat Analysis
- **Spoofing**: Defended via Argon2id hashed credentials and signed JWT tokens with expiration.
- **Tampering**: All API keys hashed with SHA-256 before storage.
- **Repudiation**: Full structlog JSON auditing on every state-changing request.
- **Information Disclosure**: Secrets managed via environment variables; non-root Docker container.
- **Denial of Service**: Rate-limiting token bucket with Redis.
- **Elevation of Privilege**: Role-based access control (RBAC) enforced in FastAPI dependencies.
