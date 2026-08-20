# Library Management System

A Django REST backend with a DTO boundary and JWT auth, and a React + TypeScript frontend, for
running a library's catalogue, circulation and membership.

Built to `specs/library-management-implementation-plan.md`.

---

## Run it

### In a container (one command)

```bash
docker compose up --build
```

Then open <http://localhost:8000>. The API and the SPA are served from the same origin; demo
data is seeded on first boot.

| | |
|---|---|
| Application | <http://localhost:8000> |
| API | <http://localhost:8000/api/v1> |
| API docs | <http://localhost:8000/api/docs> |
| Django admin | <http://localhost:8000/admin> |

**Seeded accounts** — password `LibraryDemo123!` for all of them:

| Email | Role |
|---|---|
| `librarian@library.test` | Librarian |
| `member@library.test` | Member (has overdue loans and a fine) |
| `theo@library.test` | Member |
| `nadia@library.test` | Member |

To build and run the image on its own, without Postgres (it falls back to SQLite):

```bash
docker build -t library . && docker run --rm -p 8000:8000 -e DJANGO_SECRET_KEY=dev -e SECURE_SSL_REDIRECT=False -e SEED_DEMO_DATA=true library
```

### Locally, without containers

Five commands, from a fresh clone:

```bash
cd backend && python -m venv .venv && .venv/Scripts/python -m pip install -r requirements-dev.txt
```

```bash
cd backend && .venv/Scripts/python manage.py migrate && .venv/Scripts/python manage.py seed_demo
```

```bash
cd backend && .venv/Scripts/python manage.py runserver
```

```bash
cd frontend && npm install
```

```bash
cd frontend && npm run dev
```

The frontend is then at <http://localhost:5173> and proxies `/api` to the backend. On
macOS/Linux use `.venv/bin/python` instead of `.venv/Scripts/python`.

---

## Architecture

```
library-management-system/
├── Dockerfile                 # builds the SPA, then the API image that serves both
├── docker-compose.yml         # app + postgres
├── backend/
│   ├── config/settings/       # base / local / production / test
│   ├── domains/               # the Django apps, one per bounded area
│   │   ├── common/            # base model, exceptions, error codes, handler, pagination, permissions
│   │   ├── accounts/          # User, MemberProfile, auth, members
│   │   ├── catalog/           # Author, Category, Book, BookCopy
│   │   └── circulation/       # Loan, Reservation, Fine, dashboard
│   ├── testing/factories.py   # test support; the tests themselves sit in domains/*/tests/
│   └── conftest.py
├── frontend/
│   ├── openapi.json           # exported from the Django schema
│   └── src/
│       ├── api/               # client, endpoints, typed errors, generated schema
│       ├── features/          # auth/, catalog/, circulation/, members/ — hooks AND pages
│       ├── components/        # shared UI primitives, app shell, error pages
│       ├── routes/            # the route table, and nothing else
│       ├── hooks/  lib/
└── docs/                      # conventions.md, decisions.md, api-errors.md
```

Each backend domain has the same shape — `models.py` (entities), `services.py` (writes and
workflow), `selectors.py` (reads), `dtos.py` (the wire format), `views.py`, `urls.py`,
`exceptions.py`, `tests/`. The frontend mirrors it: a feature owns its hooks *and* its pages,
so a change to circulation touches one folder.

### The layering

```
URL → View → Request DTO → Service → Model/QuerySet → Response DTO → JSON
```

Views never touch the ORM. Services never import DRF — they raise `DomainError` subclasses,
and one exception handler turns those into the single error envelope. DTOs are plain
`serializers.Serializer` classes, never `ModelSerializer`, so the wire format is chosen rather
than inherited. [docs/conventions.md](docs/conventions.md) has the full set of rules — layering,
DTO naming, error codes, the circulation policy, and the definition of done.

### The one modelling decision that matters

`Book` is the bibliographic record; `BookCopy` is a physical object on a shelf. Loans attach to
copies. Reservations attach to books, because a member wants *the title*, and the hold is bound
to a specific copy only once one comes back. Availability counts are annotated, never stored.

### Circulation rules

All tunable, in `CIRCULATION` in `config/settings/base.py`, read through
`domains/circulation/policy.py`:

| Rule | Default |
|---|---|
| Max concurrent loans | 5 |
| Loan period | 14 days |
| Max renewals | 2 |
| Renewal blocked if | the title has a reservation queue, or the loan is overdue |
| Overdue fine | £0.50/day, capped at the copy's replacement cost |
| Hold shelf time | 3 days after `READY` |
| Unpaid fine block | £10.00 |
| Suspended or expired membership | cannot borrow or reserve |

Two database constraints do the work that concurrency would otherwise defeat: a partial unique
index giving each copy at most one open loan, and one active reservation per (book, member).

### Auth

`djangorestframework-simplejwt` with the blacklist app. 15-minute access tokens, 7-day refresh
tokens, rotation with blacklist-after-rotation. `role` and `email` ride as claims so the SPA can
render the right navigation on first paint — the backend re-reads `request.user.role` on every
request and never trusts the claim. The access token lives in memory; the refresh token in
`localStorage`. That tradeoff, and how to change it, is written up in
[docs/decisions.md](docs/decisions.md).

---

## Verifying

Backend — 185 tests, 100% coverage on `domains/circulation/services.py`:

```bash
cd backend && .venv/Scripts/python -m pytest -q --cov --cov-report=term-missing
```

```bash
cd backend && .venv/Scripts/python -m ruff check . && .venv/Scripts/python -m ruff format --check .
```

Regenerate the OpenAPI schema and the TypeScript types from it:

```bash
cd backend && .venv/Scripts/python manage.py spectacular --file ../frontend/openapi.json --format openapi-json
```

```bash
cd frontend && npm run schema
```

Frontend:

```bash
cd frontend && npm run lint && npm run build && npm test
```

---

## Management commands

| Command | What it does |
|---|---|
| `manage.py seed_users` | One librarian, three members |
| `manage.py seed_catalog` | ~40 titles across 8 categories, with copies |
| `manage.py seed_demo` | Both of the above plus a live circulation state: loans out, overdues, fines, a hold queue |
| `manage.py expire_reservations` | Expires stale holds and promotes the next in each queue. Run daily. |

---

## What is deliberately not here

Email notifications, overdue reminder jobs, barcode label printing, multi-branch libraries,
inter-library loans, payment processing, full-text search inside book contents, and any audit
trail beyond `created_at`/`updated_at` and the structured action log. Each is a clean extension
once the core loop works.
