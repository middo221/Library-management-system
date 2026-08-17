# Library Management System — Implementation Plan

A phased build plan for a Django REST backend (DTO-based, JWT auth) with a React frontend.
Written to be handed to Claude Code as a working spec.

---

## 0. How to use this document

- Work **one phase at a time**. Each phase ends with an *Exit criteria* block — do not start the next phase until every box passes.
- Run the verification commands listed at the end of each phase before moving on.
- Commit at each phase boundary: `git commit -m "phase N: <name>"`.
- Copy the **Conventions** section below into a `CLAUDE.md` at the repo root so it stays in context.
- Where this plan says "decide", make a choice and record it in `docs/decisions.md` (one paragraph per decision).

### Assumptions made

These were not specified in the brief. Change them here first if any are wrong.

| Assumption | Value |
|---|---|
| Database | PostgreSQL 16 (SQLite for local dev is fine early on) |
| Python / Node | Python 3.12, Node 20+ |
| Frontend language | TypeScript |
| Roles | `LIBRARIAN` (staff) and `MEMBER` (borrower) |
| Scope | Physical copies only — no e-book files, no payment processing |
| Fines | Calculated and tracked, but marked paid manually by a librarian |

---

## 1. Conventions (copy into `CLAUDE.md`)

**Layering.** Requests flow: `URL → View → Request DTO → Service → Model/QuerySet → Response DTO → JSON`.
Views never touch the ORM directly. Services never import DRF. Models hold invariants and simple derived properties, not workflow.

**DTOs.** Every endpoint has explicit request and response DTOs in `<app>/dtos.py`.
- Use `serializers.Serializer` — **never** `ModelSerializer`. The point of the DTO boundary is that the wire format is chosen deliberately, not leaked from the schema.
- Naming: `BookCreateRequest`, `BookUpdateRequest`, `BookResponse`, `BookListItemResponse`.
- Request DTOs validate and produce a plain `dict` / dataclass. Response DTOs serialize *from* model instances or dataclasses.
- Field-level validation lives in the request DTO. Business rules (e.g. "member has reached the loan cap") live in the service and raise domain exceptions.

**Errors.** One custom exception handler returns a single envelope for every failure:

```json
{ "error": { "code": "LOAN_LIMIT_REACHED", "message": "Member already has 5 active loans.", "details": {} } }
```

Field validation errors use `code: "VALIDATION_ERROR"` with `details` keyed by field name. Never return a bare DRF error string.

**Naming.** API paths are plural, kebab-free, snake-free: `/api/v1/book-copies` is wrong; use `/api/v1/copies`. JSON keys are `snake_case` (Python-native, and the frontend maps once at the API client boundary).

**Tests.** Every service function gets a unit test. Every endpoint gets at least one happy-path and one auth-failure API test. `pytest` + `pytest-django` + `factory_boy`.

**Definition of done for any task:** code + tests pass + OpenAPI schema regenerates without errors + no new lint warnings.

---

## 2. Architecture

```
library/
├── backend/
│   ├── config/                  # settings/, urls.py, asgi.py, wsgi.py
│   │   └── settings/            # base.py, local.py, production.py
│   ├── apps/
│   │   ├── common/              # base models, exceptions, pagination, permissions, handler
│   │   ├── accounts/            # User, MemberProfile, auth endpoints
│   │   ├── catalog/             # Author, Category, Book, BookCopy
│   │   └── circulation/         # Loan, Reservation, Fine
│   ├── tests/
│   ├── manage.py
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/                 # axios client, endpoint modules, generated types
│   │   ├── features/            # auth/, catalog/, circulation/, members/
│   │   ├── components/          # shared UI primitives
│   │   ├── hooks/
│   │   ├── routes/
│   │   └── lib/
│   └── package.json
├── docker-compose.yml
└── docs/
```

Each app follows the same internal shape:

```
apps/catalog/
├── models.py
├── dtos.py          # request + response DTOs
├── services.py      # business logic, framework-free
├── selectors.py     # read queries (list/filter/annotate)
├── views.py
├── urls.py
├── permissions.py
├── exceptions.py
└── tests/
```

---

## 3. Data model

Draw this before writing code; the relationships drive everything else.

### accounts

**User** (custom, replaces `auth.User`, `AbstractBaseUser` + `PermissionsMixin`)
- `email` (unique, USERNAME_FIELD), `first_name`, `last_name`
- `role` — choices `LIBRARIAN` / `MEMBER`
- `is_active`, `is_staff`, `date_joined`

**MemberProfile** (OneToOne → User, only for `MEMBER`)
- `membership_number` (unique, generated, e.g. `M-000142`)
- `phone`, `address`
- `joined_on`, `membership_expires_on`
- `is_suspended` (blocks new loans)

### catalog

**Author** — `name`, `bio`, `birth_year`, `death_year`
**Category** — `name` (unique), `slug`, `description`
**Book** (the bibliographic record, not a physical object)
- `isbn` (unique, validated), `title`, `subtitle`
- `authors` (M2M → Author), `category` (FK → Category, nullable)
- `publisher`, `published_year`, `language`, `page_count`
- `description`, `cover_url`
- Derived (annotated, not stored): `total_copies`, `available_copies`

**BookCopy** (a physical object on a shelf)
- `book` (FK → Book, related_name `copies`)
- `barcode` (unique), `call_number` (e.g. `823.912 JOY`)
- `status` — `AVAILABLE` / `ON_LOAN` / `RESERVED` / `LOST` / `DAMAGED` / `WITHDRAWN`
- `acquired_on`, `condition_note`

> Book vs. BookCopy is the single most important modelling decision here. Loans attach to **copies**; searching and browsing happen on **books**.

### circulation

**Loan**
- `copy` (FK → BookCopy), `member` (FK → User)
- `checked_out_at`, `due_on`, `returned_at` (nullable)
- `renewal_count` (int, capped)
- `checked_out_by` / `checked_in_by` (FK → User, the librarian)
- Property `is_overdue`, `days_overdue`
- Constraint: a copy can have at most one loan with `returned_at IS NULL` (partial unique index)

**Reservation**
- `book` (FK → Book — members reserve a title, not a specific copy), `member` (FK → User)
- `status` — `PENDING` / `READY` / `FULFILLED` / `CANCELLED` / `EXPIRED`
- `reserved_at`, `ready_at`, `expires_on`, `queue_position` (derived from `reserved_at`)
- Constraint: one active reservation per (book, member)

**Fine**
- `loan` (OneToOne → Loan), `member` (FK → User)
- `amount`, `reason` (`OVERDUE` / `DAMAGE` / `LOST`)
- `assessed_on`, `paid_at`, `waived_at`, `waived_by`

### Business rules to encode in services

| Rule | Default |
|---|---|
| Max concurrent loans per member | 5 |
| Loan period | 14 days |
| Max renewals | 2 |
| Renewal blocked if | reservations exist for that book, or loan is overdue |
| Overdue fine | 0.50 / day, capped at the replacement cost |
| Reservation hold shelf time | 3 days after `READY` before it expires |
| Suspended or expired membership | cannot borrow or reserve |

Put these in `config/settings/base.py` under a `CIRCULATION` dict so they're tunable, not scattered as magic numbers.

---

## 4. API surface

Base path `/api/v1`. All responses use the error envelope from Conventions.

### Auth — `apps/accounts`

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/auth/register` | public | Creates a `MEMBER` + profile |
| POST | `/auth/login` | public | Returns `access` + `refresh` |
| POST | `/auth/refresh` | public | Rotates refresh, blacklists the old one |
| POST | `/auth/logout` | member | Blacklists the presented refresh token |
| GET | `/auth/me` | any | Current user + profile |
| PATCH | `/auth/me` | any | Update own profile fields |
| POST | `/auth/change-password` | any | Requires current password |

### Members — `apps/accounts`

| Method | Path | Auth |
|---|---|---|
| GET | `/members` | librarian |
| GET | `/members/{id}` | librarian |
| PATCH | `/members/{id}` | librarian (suspend, extend membership) |
| GET | `/members/me/loans` | member |
| GET | `/members/me/reservations` | member |
| GET | `/members/me/fines` | member |

### Catalog

| Method | Path | Auth |
|---|---|---|
| GET | `/books` | any (search, filter, paginate) |
| POST | `/books` | librarian |
| GET | `/books/{id}` | any |
| PATCH / DELETE | `/books/{id}` | librarian |
| GET | `/books/{id}/copies` | any |
| POST | `/books/{id}/copies` | librarian |
| GET/PATCH/DELETE | `/copies/{id}` | librarian |
| GET/POST | `/authors` | any / librarian |
| GET/PATCH/DELETE | `/authors/{id}` | any / librarian |
| GET/POST | `/categories` | any / librarian |

`GET /books` query params: `search` (title, subtitle, ISBN, author name), `category`, `author`, `language`, `available=true`, `ordering`, `page`, `page_size`.

### Circulation

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/loans` | librarian | filters: `status=active|overdue|returned`, `member`, `book` |
| POST | `/loans` | librarian | body: `{ barcode, member_id }` — checkout |
| GET | `/loans/{id}` | librarian or owner | |
| POST | `/loans/{id}/return` | librarian | check-in; assesses fine if overdue |
| POST | `/loans/{id}/renew` | librarian or owner | |
| GET/POST | `/reservations` | member | |
| POST | `/reservations/{id}/cancel` | owner or librarian | |
| POST | `/reservations/{id}/fulfil` | librarian | converts to a loan |
| GET | `/fines` | librarian | |
| POST | `/fines/{id}/pay` | librarian | |
| POST | `/fines/{id}/waive` | librarian | requires a reason |

### Dashboard

| Method | Path | Auth |
|---|---|---|
| GET | `/dashboard/stats` | librarian |

Returns counts: total titles, total copies, on loan, overdue, active members, reservations waiting, unpaid fines total.

---

## 5. Authentication design

Use `djangorestframework-simplejwt` with the token blacklist app enabled.

```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
}
```

- Subclass `TokenObtainPairSerializer` to add `role` and `email` claims, so the frontend can render role-appropriate navigation without an extra round trip. Never trust these claims for authorization — the backend re-checks `request.user.role` on every request.
- Permission classes in `apps/common/permissions.py`: `IsLibrarian`, `IsMember`, `IsOwnerOrLibrarian`.
- `/auth/logout` blacklists the refresh token. Access tokens stay valid until they expire — that's the stateless tradeoff, and 15 minutes is the reason the window is short.
- Rate-limit `/auth/login` and `/auth/register` with DRF throttling (`5/min` anon).

**Token storage on the client.** Keep the access token in memory (React state) and the refresh token in `localStorage`. This is the standard tradeoff for a stateless SPA: a stored refresh token is reachable by XSS, so the access token's short lifetime and a strict CSP are what limit the blast radius. If this system will ever hold real borrower data, switch the refresh token to an httpOnly, `SameSite=Strict` cookie and add CSRF protection to the refresh endpoint — note the choice in `docs/decisions.md` either way.

---

## 6. Phases

### Phase 0 — Project setup

1. `backend/` with `uv` or `pip-tools`. Dependencies: `django`, `djangorestframework`, `djangorestframework-simplejwt`, `django-cors-headers`, `django-filter`, `drf-spectacular`, `psycopg[binary]`, `python-decouple`, `pytest`, `pytest-django`, `factory-boy`, `ruff`. Pin to the current stable releases at build time.
2. Split settings: `base.py`, `local.py`, `production.py`. All secrets via env; commit a `.env.example`.
3. `docker-compose.yml` with `db` (postgres:16) and `backend`.
4. Configure `ruff` (lint + format) and pre-commit.
5. `apps/common/`: `TimeStampedModel` (`created_at`, `updated_at`), `DomainError` base exception, custom exception handler, `StandardPagination` (default 20, max 100).

**Exit criteria:** `python manage.py check` passes, `pytest` runs (zero tests is fine), containers come up.

---

### Phase 1 — Accounts and JWT

1. Custom `User` with email login + `UserManager`. Set `AUTH_USER_MODEL` **before the first migration** — getting this wrong means starting the database over.
2. `MemberProfile`, with membership number generated on creation.
3. DTOs: `RegisterRequest`, `LoginRequest`, `TokenResponse`, `UserResponse`, `MemberProfileResponse`, `ChangePasswordRequest`.
4. `services.register_member()`, `services.change_password()`.
5. Auth views and URLs; custom token serializer with role claim.
6. Permission classes in `apps/common/permissions.py`.
7. Seed command `python manage.py seed_users` — one librarian, three members.

**Exit criteria:**
- [ ] Register → login → `/auth/me` works end to end with `Bearer` header
- [ ] Refresh rotates and blacklists the old token; reusing a rotated refresh returns 401
- [ ] `/auth/me` without a token returns 401 in the standard error envelope
- [ ] A member hitting a librarian-only test endpoint gets 403
- [ ] Passwords never appear in any response DTO

Verify: `pytest apps/accounts -v`

---

### Phase 2 — Catalog

1. Models: `Author`, `Category`, `Book`, `BookCopy` + migrations. Index `isbn`, `title`, `barcode`.
2. `selectors.py`: `list_books(filters)` annotating `total_copies` and `available_copies` with a single `Count(..., filter=Q(...))` — no N+1.
3. DTOs for each resource, list vs. detail variants. `BookResponse` nests `authors` and `category` as objects, not bare IDs.
4. Services: create/update/delete with rules — can't delete a book that has copies; can't delete a copy that's on loan.
5. Views + URLs + filtering (`django-filter`) + search.
6. `drf-spectacular` wired up; `/api/schema/` and `/api/docs/` serving.
7. Seed command `seed_catalog` — ~40 books with copies.

**Exit criteria:**
- [ ] `GET /books?search=...&available=true` returns correct availability counts
- [ ] List endpoint issues a bounded number of queries regardless of page size (assert with `assertNumQueries`)
- [ ] Members get 403 on any write endpoint
- [ ] OpenAPI schema generates with no warnings

---

### Phase 3 — Circulation

The core of the system. Write the service tests first — the rules table in §3 is the test list.

1. Models `Loan`, `Reservation`, `Fine`, with the DB constraints noted above.
2. `services.checkout(barcode, member, librarian)`:
   validate copy is `AVAILABLE` → member active, not suspended, under loan cap, no unpaid fines over threshold → no *other* member's `READY` reservation on that copy → create loan, set copy `ON_LOAN`, set due date. Wrap in `transaction.atomic()` with `select_for_update()` on the copy.
3. `services.return_loan(loan, librarian)`: set `returned_at`, assess fine if overdue, then either promote the next reservation to `READY` or set the copy `AVAILABLE`.
4. `services.renew_loan(loan, actor)`: enforce renewal cap, overdue block, reservation block.
5. `services.reserve(book, member)` / `cancel_reservation` / `fulfil_reservation`.
6. Fine assessment + pay + waive.
7. Management command `expire_reservations` (run on a schedule) that moves stale `READY` reservations to `EXPIRED` and promotes the next in queue.
8. Dashboard stats selector.

**Exit criteria:**
- [ ] Two concurrent checkouts of the same copy — one succeeds, one fails cleanly (test with `select_for_update`)
- [ ] Returning an overdue loan creates a `Fine` with the correct amount
- [ ] Returning a copy with a waiting reservation sets it `RESERVED` and the reservation `READY`, not `AVAILABLE`
- [ ] Renewal is refused when a reservation queue exists
- [ ] Loan cap, suspension, and expired membership each block checkout with a distinct error code
- [ ] A member cannot read another member's loan (403, not 404-leak-free — decide and be consistent)

---

### Phase 4 — API hardening

1. Consistent error codes — collect them all in `apps/common/error_codes.py` and document in `docs/api-errors.md`.
2. Throttling: anon `100/hour`, user `1000/hour`, auth endpoints tighter.
3. CORS locked to the frontend origin.
4. Structured logging on every state-changing service call (who, what, which object).
5. Pagination, ordering, and filtering consistent across every list endpoint.
6. Export the OpenAPI schema to `frontend/openapi.json` and generate TypeScript types from it (`openapi-typescript`). The DTO layer is what makes this generation trustworthy — treat the generated types as read-only.

**Exit criteria:** `npx openapi-typescript openapi.json -o src/api/schema.d.ts` produces types that compile.

---

### Phase 5 — Frontend foundation

Stack: Vite + React + TypeScript, React Router, TanStack Query (server state), Zustand (auth state only), Tailwind, `react-hook-form` + `zod`, `axios`.

1. Scaffold, path aliases, env config (`VITE_API_BASE_URL`).
2. `src/api/client.ts` — axios instance with:
   - request interceptor attaching the in-memory access token
   - response interceptor: on 401, queue concurrent failures, refresh **once**, replay the queue; on refresh failure, clear auth and redirect to login
   - one place that unwraps the error envelope into a typed `ApiError`
3. `src/features/auth/` — auth store, `useLogin`, `useRegister`, `useMe`, `<ProtectedRoute>`, `<RoleGate role="LIBRARIAN">`.
4. App shell: navigation that differs by role, toast host, error boundary, loading and empty states.
5. Login, register, and 403/404 pages.

**Exit criteria:**
- [ ] Login persists across a page refresh (refresh token bootstraps a new access token on mount)
- [ ] An expired access token triggers exactly one refresh call even with three requests in flight
- [ ] Visiting a librarian route as a member shows the role-gate page, not a blank screen
- [ ] Hard refresh on a deep link lands on that page, not the login page, when the session is valid

---

### Phase 6 — Frontend features

**Member-facing**
- Catalog browse: search-as-you-type (debounced), category and availability filters, paginated grid, availability badge per title
- Book detail: metadata, copy list with status, "Reserve" when nothing is available
- My shelf: current loans with due dates and an overdue indicator, renew button (disabled with a reason when blocked), reservation queue position, fines owed

**Librarian-facing**
- Dashboard: the stats from `/dashboard/stats`, plus an overdue list
- Checkout screen: scan or type a barcode, then a member lookup, confirm — optimised for keyboard-only use, since this is the screen someone stands at all day
- Check-in screen: single barcode field, prominent result banner (fine assessed / hold for reservation / shelve it)
- Catalog management: book CRUD forms, copy management
- Members: list, detail with loan history, suspend or extend

**Design direction.** A library management system is a tool for people who work in a room full of catalogued objects; the interface should feel like part of that world rather than a generic admin template.

- **Palette:** ink `#161A1D`, paper `#F7F6F2`, shelf-green `#2F4A3F`, stamp-red `#9B2C2C` (reserved exclusively for overdue and destructive actions), brass `#B08D57`, rule-grey `#D8D5CD`.
- **Type:** a characterful display face for headings and book titles; a plain, highly legible sans for body and forms; a monospace for call numbers, barcodes, ISBNs, and membership numbers — these are catalogue data and should look like it.
- **Signature element:** the date-stamp motif. Due dates render as a stamped block on loan cards — slightly rotated, stamp-red when overdue. It appears in exactly one place, so it stays memorable rather than decorative.
- **Structure:** call numbers act as the visual index throughout — in list rows, on copy chips, on the check-in result. Numbering used only where order is real (the reservation queue).
- **Restraint:** everything that isn't the stamp stays quiet. Motion limited to a scroll reveal on the catalogue grid and hover states on rows; respect `prefers-reduced-motion`.
- **Copy:** buttons name the action and keep that name through the flow — "Check out" produces "Checked out". Empty states are invitations ("No loans yet. Browse the catalogue to get started."), errors state what happened and the fix, in the interface's voice.

**Exit criteria:**
- [ ] Full loop works in the UI: member reserves → librarian fulfils → librarian checks in → next reservation goes ready
- [ ] Every list has a real empty state and a loading skeleton
- [ ] Every mutation shows success and failure feedback, with the server's error message surfaced
- [ ] Keyboard-only checkout is possible start to finish
- [ ] Responsive to 375px; visible focus rings throughout

---

### Phase 7 — Quality and delivery

1. Backend coverage ≥ 80%, with 100% on `circulation/services.py`.
2. Frontend: Vitest + React Testing Library on the auth interceptor and one full feature flow.
3. One end-to-end Playwright test covering the reserve → fulfil → return loop.
4. `seed_demo` command producing a realistic dataset, including overdue loans and a reservation queue.
5. `README.md`: setup in under five commands, plus an architecture summary and the decisions log.
6. Deployment: gunicorn + whitenoise, `DEBUG=False` checklist, static frontend build, CI running lint + tests on push.

---

## 7. Build order rationale

Auth first because every other endpoint's permission tests depend on it. Catalog before circulation because loans reference copies. The frontend starts only after the OpenAPI schema is stable, so the generated types don't churn. Circulation gets written test-first because its rules are the actual product — everything else is CRUD.

## 8. Deliberately out of scope

Email notifications, overdue reminder jobs, barcode label printing, multi-branch libraries, inter-library loans, payment processing, full-text search across book contents, and an audit trail beyond `created_at`/`updated_at`. Each is a clean extension once the core loop works; none of them should compete for attention before Phase 7 passes.
