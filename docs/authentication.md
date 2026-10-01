# Authentication and authorisation

## Summary

| Aspect | Choice |
| --- | --- |
| Password hashing | Argon2id (memory-hard; resistant to GPU cracking) |
| Access token | JWT, HS256, 30 minutes, held in memory / localStorage |
| Refresh token | JWT, HS256, 14 days, **rotated on every use** |
| Refresh storage | Only a SHA-256 hash is stored; the raw token never touches the database |
| Token theft | Reuse of a rotated token revokes the entire session family |
| Signing keys | Access and refresh are signed with **different** secrets |
| Authorisation | RBAC — 52 permissions, 6 roles, one catalogue |
| CSRF | Double-submit token for cookie auth; bearer auth is exempt by construction |

---

## Registration

```
Browser                         API                            Database
   │                             │                                 │
   │  POST /api/v1/auth/register │                                 │
   │  { email, password,         │                                 │
   │    full_name, role,         │                                 │
   │    accept_terms }           │                                 │
   ├────────────────────────────▶│                                 │
   │                             │ 1. Validate (Pydantic)          │
   │                             │    email format, password policy│
   │                             │    role must be signup-assignable
   │                             │                                 │
   │                             │ 2. Check password strength      │
   │                             │    length, classes, not common   │
   │                             │                                 │
   │                             │ 3. Is the email taken?          │
   │                             ├────────────────────────────────▶│
   │                             │                                 │
   │                             │ 4. Argon2id hash                │
   │                             │                                 │
   │                             │ 5. Create user + role + profile │
   │                             │    (one transaction)            │
   │                             ├────────────────────────────────▶│
   │                             │                                 │
   │                             │ 6. Issue verification token     │
   │                             │    store sha256(token) only     │
   │                             ├────────────────────────────────▶│
   │                             │                                 │
   │                             │ 7. Queue the verification email │
   │                             │                                 │
   │                             │ 8. Create a session, issue a    │
   │                             │    token pair                   │
   │                             │                                 │
   │  201 { session, tokens }    │                                 │
   │◀────────────────────────────┤                                 │
   │                             │ 9. Audit: REGISTER              │
```

The password policy is enforced on the server and mirrored in the UI so the
user sees the rules before submitting, but the server is the authority.

When `REQUIRE_EMAIL_VERIFICATION=true` the account is created in
`PENDING_VERIFICATION` and privileged actions are refused until the address is
confirmed. The default for development is `false` so the demo flow is not
gated behind an inbox.

---

## Sign-in

```
   │  POST /api/v1/auth/login    │
   │  { email, password }        │
   ├────────────────────────────▶│
   │                             │ 1. Rate-limit bucket for /auth/*
   │                             │    (10/min per IP by default)
   │                             │
   │                             │ 2. Look the user up
   │                             │
   │                             │ 3. Verify the Argon2id hash
   │                             │    — the same work is done whether or not
   │                             │      the user exists, so timing does not
   │                             │      reveal which addresses are registered
   │                             │
   │                             │ 4. Account active? Not suspended?
   │                             │
   │                             │ 5. Trim sessions over MAX_ACTIVE_SESSIONS
   │                             │
   │                             │ 6. Create a session:
   │                             │      family_id  = new uuid
   │                             │      parent_id  = null
   │                             │      refresh_token_hash = sha256(raw)
   │                             │
   │  200 { session, tokens }    │
   │◀────────────────────────────┤
   │                             │ 7. Audit: LOGIN (with IP, user agent)
```

The response carries the user, their roles, their resolved permission set and
their `home_route`. The frontend uses the permission set to decide what to
render; the API re-checks every one of them on every request.

A failed sign-in returns the same generic message whatever went wrong. The
audit log records the detail; the response does not.

---

## Token rotation and theft detection

This is the part worth reading closely.

### Normal rotation

```
  Session family  F
  ────────────────────────────────────────────────────────────
  login      →  R1  (active)
  refresh R1 →  R2  (active)   R1 marked revoked, reason "rotated"
  refresh R2 →  R3  (active)   R2 marked revoked, reason "rotated"
```

Every refresh invalidates the token that was presented and issues a new one.
A stolen refresh token is therefore only useful until the legitimate client
refreshes next.

### Reuse detection

```
  Attacker steals R2 and uses it after the real user has already refreshed:

  refresh R2 →  R3         (real user, succeeds; R2 now revoked)
  refresh R2 →  ✗          (attacker replays R2)
                 │
                 └─▶ session.revoked_at is not null
                     ⇒ this token was already rotated
                     ⇒ two parties hold the same token
                     ⇒ the family is compromised

                 UPDATE user_sessions
                    SET revoked_at = now(),
                        revoked_reason = 'token_reuse_detected'
                  WHERE user_id = :user AND revoked_at IS NULL

                 log.warning("auth.refresh_reuse_detected")
                 401 REFRESH_TOKEN_REUSED
```

Every session for that user is revoked — the attacker's *and* the real user's.
Both must sign in again. That is the correct trade: a forced re-login is a
minor inconvenience; a silently shared session is not.

The order matters too. It is the *replay* that trips the alarm, not the
rotation, so a legitimate client that simply refreshes fast is never punished.

### The client side

```typescript
// lib/api.ts — one refresh, however many requests hit 401 at once.
let refreshInFlight: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => { /* POST /auth/refresh, store, reset */ })();
  }
  return refreshInFlight;
}
```

Without this single-flight guard, three concurrent 401s would send three
refreshes: the first rotates `R1→R2`, the second presents the now-revoked `R1`,
and the server — correctly — treats that as theft and signs the user out. The
guard is not an optimisation; it is what makes rotation and reuse detection
able to coexist with a parallel-fetching UI. It is covered by a unit test that
races three requests and asserts exactly one refresh call.

---

## Password reset

```
  POST /auth/forgot-password  { email }
        │
        ├─ Always returns: "If that email is registered, a reset link is on
        │  its way." — identical response and identical timing whether or not
        │  the address exists, so the endpoint cannot enumerate accounts.
        │
        ├─ If it does exist:
        │     raw = secrets.token_urlsafe(48)
        │     store sha256(raw), purpose=PASSWORD_RESET, expires in 60 min
        │     email {FRONTEND_URL}/reset-password?token={raw}
        │
  POST /auth/reset-password  { token, new_password }
        │
        ├─ hash the presented token, look it up
        ├─ reject if expired or already used
        ├─ validate the new password against the policy
        ├─ Argon2id hash and store
        ├─ mark the token used  (single use)
        ├─ REVOKE EVERY SESSION for that user
        └─ audit: PASSWORD_RESET
```

Revoking every session on reset is deliberate: the usual reason someone resets
a password is that they believe it is compromised, and leaving old sessions
alive would defeat the point.

The raw token exists only in the email. The database holds a SHA-256 digest,
so a database disclosure does not hand out working reset links.

---

## Email verification

The same one-time-token mechanism: `{FRONTEND_URL}/verify-email?token=…`,
48-hour expiry, single use, hash-at-rest. The frontend's verify page guards
against React's double-effect so a token is not consumed twice on mount, and
offers to resend on failure.

---

## Authorisation (RBAC)

### The catalogue

`app/core/rbac.py` holds 52 permissions as `resource:action` strings and maps
them to 6 roles. It is the single source of truth: on boot, `sync_rbac_catalogue`
reconciles the `permissions`, `roles` and `role_permissions` tables to match,
creating what is missing and updating descriptions that changed. The database
can never drift from the code.

```
STUDENT             profile:*, application:create, assessment:take,
                    portfolio:*, document:*, recommendation:read, …

ACADEMICIAN         research:*, mentorship:offer, event:create,
                    opportunity:apply, student:read (own institution), …

INDUSTRY_RECRUITER  opportunity:create, application:review,
                    application:transition, interview:schedule, …

INDUSTRY_ADMIN      everything a recruiter has, plus company:manage,
                    team:manage, analytics:read

INSTITUTION_ADMIN   student:read, placement:read, department:manage,
                    partnership:manage, report:export

SUPER_ADMIN         every permission; bypasses the permission check entirely
```

### Enforcement

```python
@router.patch(
    "/{application_id}/status",
    dependencies=[Depends(require("application:transition"))],
)
async def change_status(...):
    ...
```

Three layers, in order:

1. **Authentication** — a valid, unexpired access token signed with the access
   secret. A refresh token presented as a bearer token fails, because the
   secrets differ.
2. **Permission** — the resolved permission set for the session must contain
   the required code.
3. **Ownership** — the service layer checks that *this* recruiter's company
   owns *this* posting. A recruiter with `application:review` cannot review a
   competitor's applicants. Permission answers "may this kind of user do this
   kind of thing"; ownership answers "may this user do it to this row".

The frontend's `can()` mirrors layer 2 only, to hide controls that would be
refused. It is presentation. Removing it would make the UI confusing, not
insecure.

---

## Session inspection and revocation

`GET /auth/sessions` lists a user's active sessions with the device, IP,
creation time and last use — the current one marked. `DELETE /auth/sessions/{id}`
revokes one; signing out revokes the current one; a password change or reset
revokes all of them.

---

## What is deliberately not here

- **No refresh token in a cookie by default.** Bearer tokens in memory suit a
  single-page app talking to a separate origin, and avoid CSRF entirely. Cookie
  mode exists (`SECURE_COOKIES`, `CSRF_ENABLED`) for deployments that want it,
  and the double-submit CSRF middleware covers that path.
- **No "remember me" beyond the refresh lifetime.** Fourteen days is the
  ceiling; there is no indefinite session.
- **No social sign-in.** It would be straightforward to add — the session
  machinery does not care how a user was authenticated — but it is not
  implemented, and pretending otherwise would be worse than saying so.
- **No MFA.** The most valuable next addition; see `scalability.md`.
