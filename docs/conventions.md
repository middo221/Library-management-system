# Conventions

The rules this codebase is held to. If a change breaks one of these, either the change is
wrong or this document is — resolve it before merging, don't leave both true.

## Layering

Requests flow: `URL → View → Request DTO → Service → Model/QuerySet → Response DTO → JSON`.

- Views never touch the ORM directly. They validate with a request DTO, call a service or
  selector, and serialise with a response DTO.
- Services never import DRF. They raise `DomainError` subclasses, which the one exception
  handler turns into HTTP.
- Selectors hold read queries; services hold writes and workflow.
- Models hold invariants and simple derived properties, not workflow.

## DTOs

Every endpoint has explicit request and response DTOs in `<app>/dtos.py`.

- Use `serializers.Serializer` — **never** `ModelSerializer`. The wire format is chosen
  deliberately, not leaked from the schema.
- Naming: `BookCreateRequest`, `BookUpdateRequest`, `BookResponse`, `BookListItemResponse`.
- Request DTOs validate and produce a plain `dict`. Response DTOs serialise *from* model
  instances or dicts — never from already-serialised data.
- Field-level validation lives in the request DTO. Business rules (e.g. "member has reached
  the loan cap") live in the service and raise domain exceptions.

## Errors

One custom exception handler (`domains/common/handlers.py`) returns a single envelope for every
failure:

```json
{ "error": { "code": "LOAN_LIMIT_REACHED", "message": "Member already has 5 active loans.", "details": {} } }
```

Field validation errors use `code: "VALIDATION_ERROR"` with `details` keyed by field name.
Never return a bare DRF error string. Every code is declared in `domains/common/error_codes.py`
and documented in `docs/api-errors.md`.

## Naming

API paths are plural and unhyphenated: `/api/v1/copies`, not `/api/v1/book-copies`. JSON keys
are `snake_case`; the frontend maps once at the API client boundary.

## Circulation policy

Every tunable number lives in `CIRCULATION` in `config/settings/base.py` and is read through
`domains/circulation/policy.py`. No magic numbers in `services.py`.

## Tests

- Every service function gets a unit test. Every endpoint gets at least one happy-path and one
  auth-failure API test.
- `pytest` + `pytest-django` + `factory_boy`. Factories live in `backend/testing/factories.py`;
  shared fixtures in `backend/conftest.py`. The tests themselves live beside the code they
  cover, in `domains/<domain>/tests/`.
- `domains/circulation/services.py` is held at 100% coverage — it is the product.

## Frontend

- A feature owns its hooks **and** its pages: `features/circulation/CheckoutPage.tsx`, not
  `routes/desk/CheckoutPage.tsx`. `routes/` holds the route table and nothing else.
- Server state is TanStack Query. The only Zustand store is auth.
- Components never call `axios` directly: components → hooks → `src/api/endpoints.ts` → client.
- The error envelope is unwrapped in exactly one place (the axios response interceptor) into a
  typed `ApiError`.
- `src/api/schema.d.ts` is generated (`npm run schema`) and read-only.

## Design

Palette: ink `#161A1D`, paper `#F7F6F2`, shelf-green `#2F4A3F`, stamp-red `#9B2C2C`, brass
`#B08D57`, rule-grey `#D8D5CD`. **stamp-red is reserved for overdue state and destructive
actions.** The date-stamp motif (`components/DateStamp.tsx`) appears on loan cards and nowhere
else. Call numbers, barcodes, ISBNs and membership numbers use the mono face
(`.catalogue-data`).

## Definition of done

Code + tests pass + OpenAPI schema regenerates without warnings + no new lint warnings.

```bash
cd backend && .venv/Scripts/python -m pytest -q && .venv/Scripts/python -m ruff check . && .venv/Scripts/python manage.py spectacular --file ../frontend/openapi.json --format openapi-json
```

```bash
cd frontend && npm run lint && npm run build && npm test
```
