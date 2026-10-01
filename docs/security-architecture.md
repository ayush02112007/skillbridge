# Security architecture

## What this system holds

Before the controls, the reason for them. SkillBridge stores:

- **Credentials** for five classes of user.
- **Academic records** — institution, programme, CGPA, backlogs.
- **Assessment results** that shape a student's employment prospects.
- **Identity documents and resumes** uploaded by students.
- **Private contact details.**
- **Hiring decisions** and the reasoning behind them.

A breach here is not an inconvenience. It is someone's academic record, their
address and their rejection history in one place. The controls below are sized
for that.

---

## Threat model

| Threat | Control |
| --- | --- |
| Credential stuffing | Argon2id, per-IP rate limiting on `/auth/*` (10/min), generic failure messages, audit trail |
| Offline cracking after a database breach | Argon2id — memory-hard, tuned parameters, per-password salt |
| Session hijacking | Short-lived access tokens (30 min), refresh rotation, reuse detection revoking the family |
| Stolen refresh token | Rotation on every use; a replay revokes every session for that user |
| Token confusion | Access and refresh signed with **different** secrets, so neither is usable as the other |
| Privilege escalation | RBAC checked server-side on every request; the UI only hides, never gates |
| Horizontal access (another company's applicants) | Ownership checks in the service layer, separate from permission checks |
| Account enumeration | Identical responses and identical work for known and unknown emails on login, registration and password reset |
| SQL injection | Parameterised SQLAlchemy throughout; no string-built SQL anywhere |
| XSS | React escaping; no `dangerouslySetInnerHTML` on user content; CSP |
| CSRF | Bearer auth is immune by construction; cookie mode uses a signed double-submit token |
| Malicious upload | Magic-byte sniffing, MIME allow-list, size cap, randomised names, path containment, optional AV hook |
| Document leakage | Private by default; every download is an authorisation check plus a short-lived signed URL |
| Mass assignment | Explicit Pydantic schemas; ORM models are never populated from raw request bodies |
| Secret disclosure via logs | Structured logger redacts any key matching a secret-shaped name |
| Secret disclosure via the bundle | No `NEXT_PUBLIC_` secret exists; a CI job fails the build if one appears |
| Misconfigured production | Startup validation refuses to boot with dev secrets, debug on, or wildcard CORS/hosts |
| Denial of service | Rate limits in middleware and in Nginx, pagination caps, upload caps, connection pooling |
| Insider access to student records | Append-only audit log with actor, IP and user agent |

---

## Authentication

Covered in detail in [`authentication.md`](authentication.md). In brief:

- **Argon2id** for passwords, with a server-enforced policy (length, character
  classes, common-password rejection) mirrored in the UI for feedback.
- **JWT access tokens**, 30 minutes, signed with `JWT_SECRET`.
- **Refresh tokens**, 14 days, signed with `JWT_REFRESH_SECRET`, rotated on
  every use, stored only as a SHA-256 digest.
- **Reuse detection**: presenting an already-rotated refresh token revokes
  every session for that user and logs `auth.refresh_reuse_detected`.
- **One-time tokens** for verification and reset: hashed at rest, single use,
  time-limited; a reset revokes all sessions.

---

## Authorisation

Three distinct checks, in order. Conflating them is how horizontal access bugs
happen.

```
1. Authenticated?   A valid, unexpired access token signed with the access
                    secret. A refresh token presented as a bearer fails.

2. Permitted?       The resolved permission set contains the required
                    `resource:action` code. 52 permissions, 6 roles, defined
                    once in app/core/rbac.py and synced to the database on boot.

3. Entitled?        Service-layer ownership: is this *this* recruiter's
                    posting? This student's document? This institution's
                    cohort? Permission says what kind of thing you may do;
                    ownership says which rows you may do it to.
```

The frontend's `can()` mirrors step 2 only, to avoid rendering controls that
would be refused. Deleting it would make the UI confusing, not insecure — every
check is re-performed server-side.

---

## Input handling

**Validation at the boundary.** Every request body and query string is a
Pydantic v2 model: types coerced, ranges enforced, unknown fields rejected,
strings length-bounded. Nothing reaches a service function unvalidated.

**Invariants in the database.** Validation can be bypassed by a future code
path; a constraint cannot.

```sql
CHECK ((student_id IS NOT NULL) <> (academician_id IS NOT NULL))  -- applications
CHECK (score >= 0 AND score <= 100)                               -- student_skills
UNIQUE (opportunity_id, student_id)                               -- no duplicates
```

The score constraint caught a real bug during development: the seeder computed
`EXPERT (4 × 25) + jitter` and exceeded 100. The database refused the write.
That is the constraint doing exactly its job.

**No mass assignment.** ORM models are never constructed from `**request.dict()`.
Each service function names the fields it sets.

---

## Uploads

```
1. Size          rejected above MAX_UPLOAD_SIZE_MB before the body is read fully
2. Magic bytes   the file's actual signature is read; the declared
                 Content-Type is treated as a hint, never as evidence
3. Allow-list    PDF, PNG, JPEG, WEBP, DOC, DOCX by default (configurable)
4. Storage key   randomised; the original filename is stored as metadata only,
                 so "../../etc/passwd.pdf" is never a path
5. Containment   the resolved path is asserted to be inside the storage root
6. Checksum      SHA-256 recorded for integrity and duplicate detection
7. Scan hook     VIRUS_SCAN_ENABLED gates a pluggable scanner
```

Serving is equally restricted: `is_public` defaults to false, access requires
ownership or an unexpired grant in `document_access_grants`, every access is
audited, and the response is a signed URL that expires in 15 minutes rather
than the bytes themselves.

---

## Transport and headers

Applied by middleware, and again by Nginx in production:

| Header | Value |
| --- | --- |
| `Content-Security-Policy` | `default-src 'self'` with explicit allowances on the docs routes; `default-src 'none'` on the API itself |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (production only) |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | camera, microphone, geolocation, payment all denied |

CORS uses an explicit origin list. `validate_runtime()` refuses to start
production if it contains `*`.

Password-reset and verification pages set `robots: noindex` and
`referrer: no-referrer`, so a token in a URL is neither indexed nor leaked to a
third party through the Referer header.

---

## Rate limiting

Two layers, because they catch different things.

**In the application** — per-IP token buckets, with a tighter bucket for
authentication:

```
RATE_LIMIT_DEFAULT_PER_MINUTE = 300
RATE_LIMIT_AUTH_PER_MINUTE    = 10     login, register, reset, refresh
RATE_LIMIT_WRITE_PER_MINUTE   = 60
```

Exceeding a bucket returns `429` with `Retry-After`.

**In Nginx** — because the in-process limiter cannot see traffic spread across
replicas:

```nginx
limit_req_zone $binary_remote_addr zone=api_auth:10m  rate=1r/s;
limit_req_zone $binary_remote_addr zone=api_write:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=api_read:10m  rate=30r/s;
limit_conn_zone $binary_remote_addr zone=conn_per_ip:10m;
```

---

## Secrets

| Rule | How it holds |
| --- | --- |
| Secrets come from the environment | `pydantic-settings`; nothing is read from a committed file |
| No secret in source | `.env` is git-ignored; only `.env.example` is committed, with sentinel values |
| No secret in the frontend bundle | Only `NEXT_PUBLIC_*` reaches the browser, and a CI job fails the build if one is named like a secret |
| No secret in logs | The structured logger redacts keys matching password/token/secret/authorization before emitting |
| Production cannot run on dev secrets | `validate_runtime()` aborts the boot |

```python
# app/core/logging.py
_SENSITIVE_KEYS = {
    "password", "new_password", "current_password", "token", "access_token",
    "refresh_token", "authorization", "secret", "api_key", "jwt_secret",
    "s3_secret_key", "smtp_password",
}
```

Redaction happens in the processor chain, so it applies to every log line
regardless of which call site produced it. A future `log.info("x", password=…)`
is redacted automatically rather than depending on the author remembering.

---

## Audit

An append-only log of security-relevant actions: authentication events,
password changes, permission and role changes, application status transitions,
document access, data exports and administrative actions.

Each entry records the actor, the action, the resource type and id, the IP
address, the user agent and a timestamp. There is no update or delete path in
the application — the table is written to and read from, never modified.

This exists partly for incident response and partly for the students: when an
institution can see a student's records, the student's ability to know that it
happened depends on somebody having written it down.

---

## Error handling

Domain exceptions carry a machine-readable code and are mapped by a single
handler:

```json
{ "success": false,
  "error": { "code": "INVALID_TRANSITION",
             "message": "An application cannot move from SELECTED to APPLIED.",
             "details": { "allowed": [] } } }
```

No stack trace reaches a client. No internal path, SQL fragment or library
version appears in a message. Unhandled exceptions log with the request id and
return a generic 500 — and the request id is what a user can quote to support
without exposing anything.

---

## Dependencies

`requirements.txt` and `package-lock.json` pin exact versions. A weekly CI job
runs `pip-audit` and `npm audit`, and CodeQL runs on every pull request for
both languages.

---

## Deliberately out of scope

Stating these is part of the security posture; pretending otherwise would be
worse.

- **No multi-factor authentication.** The highest-value addition, and the
  session machinery would accommodate it without redesign. It is not built.
- **No field-level encryption at rest.** Data relies on database-level
  encryption provided by the deployment. Documents in S3 rely on bucket
  encryption.
- **No WAF.** Nginx rate limiting is not a substitute for one in front of a
  public deployment.
- **No penetration test.** The controls above are designed and tested, not
  adversarially validated by a third party.
- **Virus scanning is a hook, not an implementation.** `VIRUS_SCAN_ENABLED`
  gates an interface that a real scanner must be wired into.
- **No anomaly detection.** Reuse detection catches one specific attack. There
  is no behavioural monitoring.

---

## If you deploy this

The application refuses to start if the first item is wrong. The rest are
yours:

- [ ] `JWT_SECRET` and `JWT_REFRESH_SECRET` unique, random, and different from
      each other — 64 bytes from a CSPRNG
- [ ] Every other credential changed from its development value
- [ ] `ENVIRONMENT=production`, `DEBUG=false`, `SECURE_COOKIES=true`
- [ ] `CORS_ORIGINS` and `TRUSTED_HOSTS` list real values, never `*`
- [ ] `REQUIRE_EMAIL_VERIFICATION=true`
- [ ] `SEED_ON_START=false`, and no demo account exists in the database
- [ ] TLS terminating at Nginx with a valid certificate; HTTP redirects
- [ ] Database not reachable from the public internet
- [ ] Backups configured, and a restore actually tested
- [ ] Log aggregation in place, with alerting on
      `auth.refresh_reuse_detected`
