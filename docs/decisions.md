# Decisions

One paragraph per decision, in the order they were taken. Where the plan said "decide", the
answer is here.

## Django 6.1 on Python 3.13/3.14

The plan assumed Python 3.12; the build machine runs 3.14.2, so dependencies were pinned to
the current stable releases that support it — Django 6.1, DRF 3.18, simplejwt 5.5. The
container image uses `python:3.13-slim`, which is the newest slim tag with wheels for every
pinned dependency. `requirements.txt` carries exact pins; `requirements-dev.txt` adds the test
and lint tooling so the runtime image never installs pytest.

## SQLite for local development, Postgres everywhere else

`config/settings/local.py` falls back to SQLite when `DB_ENGINE` is unset, so a fresh clone
runs with no services. Both compose files set `DB_ENGINE` to Postgres 16, and the test settings
use in-memory SQLite for speed. The only behaviour this hides is `select_for_update`, which
SQLite accepts and ignores — the partial unique index on `Loan` is what actually prevents a
double checkout, and that constraint is exercised directly in
`domains/circulation/tests/test_checkout.py::TestConcurrency`.

## A member reading someone else's loan gets 403, not 404

The plan asked for a decision and consistency. Every ownership check answers **403
PERMISSION_DENIED**. Hiding existence behind a 404 would only help if loan ids were secret, and
they are not — they come from a list the requester already saw, or from a URL someone shared.
A truthful status is easier to act on, and the message says what to do. This is applied in
`_assert_can_view` in `domains/circulation/views.py` and covers loans, reservations and fines.

## Reserving an available title holds a copy immediately

The plan describes "Reserve" as the action when nothing is available. Rather than refuse a
reservation on an available title, `services.reserve` creates the reservation and, if a copy is
on the shelf, promotes it straight to `READY` and marks the copy `RESERVED`. A member who
reserves something in stock gets a definite answer ("we are holding it until Thursday") instead
of a queue position of 1 behind nobody, and the librarian's fulfil flow works from a single
state. Titles that are all out still produce a `PENDING` queue.

## The loan cap governs holding, not queueing

`assert_member_can_borrow` takes `check_loan_cap`. Checkout enforces the cap; reserving does
not. Someone at their limit can still join a queue for the next thing they want to read — the
cap is applied when the hold is fulfilled, which is the moment they would actually be holding a
sixth book. Suspension, expiry and the unpaid-fine threshold block both.

## Fulfilment routes through `checkout`

`fulfil_reservation` frees the held copy and then calls `checkout` rather than writing its own
`Loan`. Every borrowing rule — cap, suspension, expiry, fines, the copy's own state — is
therefore enforced in exactly one place, and a hold cannot be used as a way around a rule that
would refuse the same member at the desk.

## Refresh token in localStorage, access token in memory

As the plan's §5 sets out, this is the standard stateless-SPA tradeoff: the stored refresh
token is reachable by XSS, and the fifteen-minute access lifetime plus rotation-with-blacklist
is what limits the blast radius. The access token is never written to storage, so a page
refresh spends the refresh token to bootstrap a new one — which is also what makes a hard
refresh on a deep link land on that page. **If this system is ever to hold real borrower data,
move the refresh token to an httpOnly, `SameSite=Strict` cookie and add CSRF protection to
`/auth/refresh`.** That is a backend change to `domains/accounts/views.py` plus a client change to
`src/api/tokens.ts`; nothing else depends on where the token lives.

## One refresh, however many requests are in flight

`refreshAccessToken` memoises the in-flight promise. Three requests that hit a 401 together all
await the same call, then replay with the new token. The alternative (a queue of deferred
requests) is more code for the same behaviour. Verified in `src/api/client.test.ts`.

## One container serves the API and the SPA

The root `Dockerfile` builds the React app in a Node stage and copies `dist/` into the Django
image, where WhiteNoise serves the hashed assets and a catch-all view returns `index.html` for
client routes. Same origin means no CORS configuration in production and no second web server
to keep in step. In development the two run apart — `manage.py runserver` and `npm run dev` —
with Vite's dev proxy forwarding `/api` so the same-origin arrangement holds there too. A
container stack that hot-reloaded both was built and then dropped: it duplicated the native
workflow without being faster, and the two extra Dockerfiles it needed were pure upkeep.

## Membership numbers are labels, not keys

`M-000142` is generated from the profile's row id at creation. It is unique and sequential but
gap-tolerant: a deleted profile leaves a hole, and that is fine, because nothing joins on it.
Every lookup is by primary key or email.

## Fines are assessed automatically, settled by hand

Returning an overdue loan creates a `Fine` at `0.50`/day capped at the copy's replacement cost
(or the configured default). Payment and waiving are librarian actions with their own
endpoints; waiving requires a reason, which is stored. Damage and loss are judgement calls, so
`assess_manual_fine` exists for a librarian to use rather than being derived from dates.

## `apps/` renamed to `domains/`, pages moved in with their features

A deviation from the plan's §2 tree, taken deliberately after it was built. `apps/` is the
Django convention and was not wrong, but `domains/` says what the directories actually are —
bounded areas of the library, each with its own entities, services and wire format. The rename
is cosmetic where it counts: every `AppConfig` sets an explicit `label`, so the app labels stay
`accounts`/`catalog`/`circulation`, `AUTH_USER_MODEL` still resolves, and no migration moved.
`backend/tests/` became `backend/testing/`, because it only ever held factories — the tests
themselves live in `domains/<domain>/tests/`.

On the frontend the same principle fixed a genuine inconsistency: feature *logic* had been in
`features/` while feature *UI* sat in `routes/desk/`. Pages now live with the feature that owns
them, `routes/` holds only the route table, and the member hooks moved out of
`features/circulation/` into `features/members/`, which the plan's §2 listed all along. URLs are
unchanged — `/desk/checkout` is still `/desk/checkout`, because that is what the people standing
at the desk call it.

## `expire_reservations` is a management command, not a scheduler

The plan puts scheduled jobs out of scope, so the command exists and is idempotent, and how it
gets run daily (cron, a compose sidecar, a platform scheduler) is a deployment decision rather
than an application one.
