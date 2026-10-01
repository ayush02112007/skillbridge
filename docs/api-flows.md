# API flows

Sequence diagrams for the journeys that matter. Each one is the actual call
sequence, not an idealised version.

---

## Conventions

Every successful response:

```json
{ "success": true, "data": { … }, "meta": { … } }
```

Every error response:

```json
{ "success": false,
  "error": { "code": "ALREADY_APPLIED",
             "message": "You have already applied to this opportunity.",
             "details": { } } }
```

Error codes are stable strings the frontend can branch on. HTTP status conveys
the category; the code conveys the cause.

List endpoints paginate with `?page=&page_size=` and return
`meta: { page, page_size, total, pages }`.

---

## 1. Registration through to a first recommendation

```
Student        Frontend              API                   Engine        DB
   │              │                   │                      │           │
   │ fill form    │                   │                      │           │
   ├─────────────▶│                   │                      │           │
   │              │ POST /auth/register                      │           │
   │              ├──────────────────▶│                      │           │
   │              │                   │ validate, hash (Argon2id)        │
   │              │                   ├─────────────────────────────────▶│
   │              │                   │ create user + role + profile     │
   │              │                   │ issue session + token pair       │
   │              │ 201 {session,tokens}                     │           │
   │              │◀──────────────────┤                      │           │
   │              │ store tokens, route to /student/dashboard│           │
   │              │                   │                      │           │
   │              │ GET /students/me/dashboard               │           │
   │              ├──────────────────▶│                      │           │
   │              │                   │ profile completion, readiness,   │
   │              │                   │ applications, deadlines          │
   │              │ 200 {…}           │                      │           │
   │◀─────────────┤                   │                      │           │
   │              │                   │                      │           │
   │              │ GET /recommendations/opportunities       │           │
   │              ├──────────────────▶│                      │           │
   │              │                   │ load candidate snapshot          │
   │              │                   ├─────────────────────▶│           │
   │              │                   │  match() per posting │           │
   │              │                   │  rank, attach reasons│           │
   │              │                   │◀─────────────────────┤           │
   │              │ 200 [{score, reasons, matching, missing}]│           │
   │◀─────────────┤                   │                      │           │
```

A brand-new student with no assessments still gets recommendations — based on
declared interests, education and location — and the reasons say so. There is
no empty state pretending to be a result.

---

## 2. Taking an assessment

```
Student      Frontend             API                Engine          DB
   │            │                  │                    │             │
   │            │ GET /assessments  │                    │             │
   │            ├─────────────────▶│                    │             │
   │            │ 200 [{skill, questions, attempts_used, can_attempt}] │
   │            │◀─────────────────┤                    │             │
   │  Start     │                  │                    │             │
   ├───────────▶│ POST /assessments/{id}/attempts        │             │
   │            ├─────────────────▶│                    │             │
   │            │                  │ check attempts remaining          │
   │            │                  │ load questions WITHOUT is_correct │
   │            │                  ├──────────────────────────────────▶│
   │            │                  │ create attempt (IN_PROGRESS)      │
   │            │ 201 {attempt_id, questions[], expires_at}            │
   │            │◀─────────────────┤                    │             │
   │            │                  │                    │             │
   │  answer ×N │ (held client-side; no round trip per question)       │
   ├───────────▶│                  │                    │             │
   │            │                  │                    │             │
   │  Submit    │ POST /assessments/attempts/{id}/submit │             │
   ├───────────▶├─────────────────▶│                    │             │
   │            │                  │ load attempt with questions       │
   │            │                  │   .execution_options(             │
   │            │                  │       populate_existing=True)     │
   │            │                  │ score_attempt()    │             │
   │            │                  ├───────────────────▶│             │
   │            │                  │   difficulty weights              │
   │            │                  │   partial credit, penalties       │
   │            │                  │   per-skill breakdown             │
   │            │                  │◀───────────────────┤             │
   │            │                  │ write attempt_skill_scores        │
   │            │                  │ upsert student_skills             │
   │            │                  │   (measured overrides self-report)│
   │            │                  │ invalidate gap analysis + recs    │
   │            │                  ├──────────────────────────────────▶│
   │            │ 200 {score, per-skill levels, confidence, feedback}  │
   │◀───────────┤                  │                    │             │
```

The `populate_existing=True` is load-bearing. `Assessment.questions` is
configured `lazy="raise"`, and an earlier `lazy="noload"` meant SQLAlchemy
treated the collection as *loaded but empty* — so a later eager query returned
the identity-mapped object with no questions and every attempt would have
scored zero. The explicit repopulation fixes it; the `lazy="raise"` makes the
silent-empty case loud if it ever recurs.

---

## 3. Skill gap and learning path

```
Frontend                    API                    Engine            DB
   │  GET /students/me/skill-gap?role_id=…          │                 │
   ├───────────────────────▶│                       │                 │
   │                        │ load held skills + role requirements     │
   │                        ├─────────────────────────────────────────▶│
   │                        │ analyse_gap()         │                 │
   │                        ├──────────────────────▶│                 │
   │                        │   per skill: severity, importance,       │
   │                        │   market signal → priority               │
   │                        │   overall readiness                      │
   │                        │◀──────────────────────┤                 │
   │                        │ persist the analysis  │                 │
   │  200 {readiness, items[], summary}             │                 │
   │◀───────────────────────┤                       │                 │
   │                        │                       │                 │
   │  GET /learning/path?role_id=…                  │                 │
   ├───────────────────────▶│                       │                 │
   │                        │ build_learning_path() │                 │
   │                        ├──────────────────────▶│                 │
   │                        │   topological pass over PREREQUISITES    │
   │                        │   then priority within each tier         │
   │                        │   effort estimate per step               │
   │                        │◀──────────────────────┤                 │
   │                        │ attach institution programmes            │
   │  200 {steps[] in order, each with why and how long}              │
   │◀───────────────────────┤                       │                 │
```

---

## 4. Browsing and applying

```
Student   Frontend              API                            DB
   │         │                   │                              │
   │ filters │ GET /internships?location=&skills=&mode=&page=   │
   ├────────▶├──────────────────▶│                              │
   │         │                   │ one query across the joined  │
   │         │                   │ opportunity hierarchy        │
   │         │                   │ + per-row match score for    │
   │         │                   │   the signed-in student      │
   │         │ 200 {data[], meta}│                              │
   │◀────────┤                   │                              │
   │         │                   │                              │
   │ open    │ GET /opportunities/{id}                          │
   ├────────▶├──────────────────▶│                              │
   │         │                   │ posting + company + skills   │
   │         │                   │ + match breakdown            │
   │         │                   │ + has_applied, is_saved      │
   │         │                   │ + eligibility check          │
   │         │ 200 {…}           │                              │
   │◀────────┤                   │                              │
   │         │                   │                              │
   │ Apply   │ POST /applications { opportunity_id, cover_letter }
   ├────────▶├──────────────────▶│                              │
   │         │                   │ 1. posting is PUBLISHED and open
   │         │                   │ 2. deadline has not passed   │
   │         │                   │ 3. no existing application   │
   │         │                   │    (unique constraint backs this)
   │         │                   │ 4. eligibility re-checked server-side
   │         │                   │ 5. SNAPSHOT the match score, the
   │         │                   │    breakdown, matched and missing
   │         │                   │    skills onto the application
   │         │                   │ 6. status = APPLIED, history row
   │         │                   │ 7. notify the recruiter (queued)
   │         │                   ├─────────────────────────────▶│
   │         │ 201 {application}  │                             │
   │◀────────┤                   │                              │
```

The snapshot in step 5 matters: a recruiter opening the application next month
sees the score as it was at submission. Recomputing on read would mean the
score quietly changed after the student applied, which is neither fair to the
candidate nor useful to the recruiter.

Applying twice returns `409 ALREADY_APPLIED`. The unique constraint means a
race between two tabs cannot create two rows.

---

## 5. Recruiter review and shortlisting

```
Recruiter  Frontend               API                             DB
   │          │                    │                               │
   │ filters  │ GET /applications/received?status=&min_match_score= │
   ├─────────▶├───────────────────▶│                               │
   │          │                    │ scoped to the recruiter's      │
   │          │                    │ company — ownership, not just  │
   │          │                    │ permission                     │
   │          │ 200 {data[], meta} │                               │
   │◀─────────┤                    │                               │
   │          │                    │                               │
   │ open one │ GET /applications/{id}                              │
   ├─────────▶├───────────────────▶│                               │
   │          │                    │ applicant profile, skills,     │
   │          │                    │ the snapshotted breakdown,     │
   │          │                    │ timeline, documents they       │
   │          │                    │ chose to attach                │
   │          │ 200 {…}            │                               │
   │◀─────────┤                    │                               │
   │          │  UI shows: "The match score is decision support …   │
   │          │   the hiring decision remains yours."               │
   │          │                    │                               │
   │Shortlist │ PATCH /applications/{id}/status                     │
   ├─────────▶├───────────────────▶│ { status: "SHORTLISTED", note }│
   │          │                    │ 1. permission application:transition
   │          │                    │ 2. ownership: this company's posting
   │          │                    │ 3. APPLICATION_TRANSITIONS allows
   │          │                    │    APPLIED → SHORTLISTED       │
   │          │                    │ 4. update + history row with the
   │          │                    │    actor's identity            │
   │          │                    │ 5. notify the student (queued) │
   │          │                    ├──────────────────────────────▶│
   │          │ 200 {application}  │                               │
   │◀─────────┤                    │                               │
   │          │ invalidate list, counts and detail queries          │
```

An invalid transition — say `SELECTED → APPLIED` — returns
`422 INVALID_TRANSITION` with the permitted targets in `details`. The state
machine lives in `APPLICATION_TRANSITIONS` and a frontend contract test asserts
the recruiter UI never offers a transition the API would refuse.

---

## 6. Document upload and access

```
Owner    Frontend            API                    Storage         DB
  │         │                 │                        │             │
  │ choose  │ POST /documents (multipart)              │             │
  ├────────▶├────────────────▶│                        │             │
  │         │                 │ 1. size ≤ MAX_UPLOAD_SIZE_MB
  │         │                 │ 2. sniff MAGIC BYTES — the declared
  │         │                 │    content type is not trusted
  │         │                 │ 3. extension and MIME allow-list
  │         │                 │ 4. randomised storage key; the
  │         │                 │    original filename is metadata only
  │         │                 │ 5. path containment check
  │         │                 ├───────────────────────▶│             │
  │         │                 │ 6. record: owner, checksum, size,
  │         │                 │    is_public = false   │             │
  │         │                 ├─────────────────────────────────────▶│
  │         │ 201 {document}  │                        │             │
  │◀────────┤                 │                        │             │

Later, a recruiter requests it:

  │         │ GET /documents/{id}/download              │             │
  ├────────▶├────────────────▶│                        │             │
  │         │                 │ 1. owner? OR an unexpired grant in
  │         │                 │    document_access_grants?           │
  │         │                 │ 2. audit the access   │             │
  │         │                 │ 3. mint a signed URL, 15-minute TTL  │
  │         │ 200 {url, expires_at}                    │             │
  │◀────────┤                 │                        │             │
  │  browser fetches the signed URL directly ─────────▶│             │
```

No document is ever served from a public path. There is no code path that does
it, which is a stronger guarantee than a flag that defaults to private.

---

## 7. Token refresh under concurrency

```
Three requests fire at once with an expired access token.

  req A ──▶ 401          req B ──▶ 401          req C ──▶ 401
     │                      │                      │
     └──────────┬───────────┴──────────────────────┘
                ▼
       refreshTokens()  ── first caller creates the promise;
                           B and C await the same one
                ▼
       POST /auth/refresh   ← exactly one request
                ▼
       rotate R1 → R2, store, resolve
                ▼
     ┌──────────┴───────────┬──────────────────────┐
     ▼                      ▼                      ▼
  replay A               replay B               replay C
  with R2's access       with R2's access       with R2's access
```

Without the single-flight guard, B would present the already-rotated R1, the
server would detect reuse, and every session for that user would be revoked —
turning a routine token expiry into a forced sign-out. The guard is covered by
a unit test that races three requests and asserts exactly one refresh call.

---

## 8. Analytics export

```
Institution  Frontend          API                  Engine         DB
    │           │               │                      │            │
    │           │ GET /analytics/institution?from=&to= │            │
    │           ├──────────────▶│                      │            │
    │           │               │ cache lookup (Redis or in-process)│
    │           │               │ miss → aggregate:    │            │
    │           │               │   readiness distribution          │
    │           │               │   placement rates by department   │
    │           │               │   top skill gaps across the cohort│
    │           │               │   employer engagement             │
    │           │               ├──────────────────────────────────▶│
    │           │               │ cache for CACHE_DEFAULT_TTL       │
    │           │ 200 {…}       │                      │            │
    │◀──────────┤               │                      │            │
    │           │               │                      │            │
    │ Export    │ GET /analytics/institution/export?format=pdf      │
    ├──────────▶├──────────────▶│                      │            │
    │           │               │ same aggregates → reportlab       │
    │           │ 200 application/pdf (streamed)       │            │
    │◀──────────┤  downloadFile() hands it to the browser           │
```

Aggregate analytics are the only thing cached, because they are the only thing
expensive enough to justify the staleness. Nothing that affects an individual's
application or score is served from cache.
