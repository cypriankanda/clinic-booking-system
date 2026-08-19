# Clinic Connect

Clinic Booking API

A REST API for a small clinic (5 doctors, 30-minute slots) to let patients view availability, book, cancel, and reschedule appointments — built for the Savannah Informatics backend take-home assessment.

Section 1 — System Design

The scenario, restated

Five doctors, each with fixed weekly working hours, working in 30-minute slots. Patients view a doctor's free slots for a given day, book one, and that slot becomes unavailable to everyone else. Patients can cancel and reschedule. The system should be simple now but not painted into a corner — the clinic wants to grow.

Models

Doctor            id, name, specialty (nullable)
WorkingHours      id, doctor_id (FK), day_of_week, start_time, end_time
                  UNIQUE(doctor_id, day_of_week)
Patient           id, name, email (unique)
Appointment       id, doctor_id (FK), patient_id (FK),
                  slot_start, slot_end, status (booked|cancelled),
                  cancellation_reason, created_at, updated_at
                  UNIQUE(doctor_id, slot_start) WHERE status = 'booked'

Key decisions and trade-offs

Slots are derived, not stored. I didn't create a Slot table that gets pre-generated for every doctor/day. Instead, GET /doctors/{id}/availability computes the full grid of 30-minute slots from WorkingHours at read time and subtracts whatever's already booked in Appointment. This keeps the source of truth in one place (no risk of a Slot table drifting out of sync with working hours) and avoids needing a background job to generate future slots. The trade-off: the availability query does more computation per request. At 5 doctors and a handful of requests a day, that's free. If the clinic grows to hundreds of doctors with heavy traffic, I'd introduce a materialized/cached slots table refreshed on a schedule — but building that now would be solving a problem this clinic doesn't have yet.

The double-booking guard lives in the database, not just the application. The scenario's one hard requirement — "once booked, that slot must not be available to others" — is a concurrency problem, not a validation problem. Two patients can hit "book" on the same slot within milliseconds of each other; an application-level if not booked: book() check has a race window between the check and the write. I handle this with a partial unique index: UNIQUE(doctor_id, slot_start) WHERE status = 'booked'. The application still does an optimistic pre-check first (so the common case gets a fast, friendly response), but the actual guarantee is the database rejecting the losing insert with an IntegrityError, which the service layer catches and turns into a clean 409 Conflict. This holds even if the app runs multiple instances behind a load balancer — the guarantee doesn't depend on anything in-process. See app/services/booking_service.py and tests/test_concurrency.py, which spins up two real threads racing to book the same slot and asserts exactly one wins.

Reschedule updates the same row rather than cancel+recreate. Moving an appointment changes slot_start/slot_end on the existing row in a single UPDATE, inside one transaction. That makes "free the old slot, claim the new one" atomic by construction — there's no window where both slots are briefly free (or briefly double-claimed), and it's still protected by the same unique index if a concurrent booking targets the new slot.

All datetimes are UTC, converted at the API boundary. Clients send timezone-aware ISO 8601 timestamps; everything internal — validation, slot math, storage — works in UTC. I built a custom UTCDateTime SQLAlchemy type after finding, while testing reschedule, that SQLite silently drops timezone info on read-back even when the column is declared DateTime(timezone=True) — which meant a freshly-booked slot's stored datetime wasn't equality-matching the datetime the availability query was excluding it against. The type normalizes every datetime to naive-UTC on write and re-attaches tzinfo=UTC on read, so behavior is identical on SQLite (used for local dev/tests) and Postgres (production).

Cancelled appointments don't block rebooking the slot. The unique index is partial (WHERE status = 'booked'), so a cancelled appointment leaves no trace blocking that doctor/slot combination — someone else can book it immediately.

The 1-hour minimum booking notice (bonus) applies to both fresh bookings and reschedules, and is also reflected in GET availability — a slot 20 minutes from now won't show as "available" even though technically no one's booked it, since attempting to book it would fail anyway. This felt more honest than showing a slot as available and then rejecting the booking.

Ambiguous decisions I made and noted here, per the instructions:

"Within working hours" is inclusive of the start time and requires the full 30-minute slot to end at or before the closing time (a slot starting 5 minutes before closing is rejected, not truncated).

A doctor with no WorkingHours row for a given weekday is treated as not working that day at all (empty availability, booking rejected) rather than an error — this seemed like the more common real-world case (e.g., doctor doesn't work weekends) than a misconfiguration.

Appointment slots must align exactly to the 30-minute grid relative to midnight UTC; a POST /appointments with slot_start off-grid (e.g. 09:15) is rejected as a validation error rather than silently rounded.

Architecture

Client
  |
  v
FastAPI routers (appointments / doctors / patients)
  |  - HTTP <-> service translation only
  v
BookingService
  |  - all business rules + concurrency handling
  v
Repositories (Appointment / Doctor / Patient)
  |  - raw queries only, no business logic
  v
SQLAlchemy models -> PostgreSQL (prod) / SQLite (local & tests)

Errors raised anywhere in the service layer are custom exceptions (NotFoundError, ValidationFailedError, ConflictError) caught by a single FastAPI exception handler (app/error_handlers.py) and translated into a consistent JSON shape:

{ "error": "SLOT_ALREADY_BOOKED", "message": "..." }

Section 2 — Running Locally

Option A: Docker Compose (recommended — matches production DB)

docker-compose up --build

This starts Postgres, seeds 5 doctors (Mon–Fri, 09:00–17:00) and 2 sample patients, and runs the API on http://localhost:8000. Interactive API docs are at http://localhost:8000/docs.

Option B: Local Python (SQLite, zero external dependencies)

python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload

Running tests

pytest -q

19 tests: booking validation, cancel/reschedule state transitions, and a genuine multi-threaded concurrency test (tests/test_concurrency.py) that proves the double-booking guard under real simultaneous requests, not just sequential ones.

Endpoints

Method Path Description POST /appointments Book a slot GET /doctors/{id}/availability?date=YYYY-MM-DD Free 30-min slots for a doctor on a date PATCH /appointments/{id}/cancel Cancel an appointment PATCH /appointments/{id}/reschedule Move an appointment to a new slot GET /patients/{id}/appointments Upcoming appointments, sorted by date (bonus) GET /health Liveness check

Section 3 — Deployment & CI/CD

Public URL: add after deploying

Branch that triggers deployment: main — the deploy job in .github/workflows/deploy.yml runs only on a push to main (i.e., after a PR is merged), and only if the test job passes first.

What the pipeline does:

On every pull request against main: installs dependencies, lints with ruff, runs the full pytest suite.

On merge to main: re-runs the same checks, then triggers a deploy via the hosting provider's deploy hook (DEPLOY_HOOK_URL secret) — this keeps the workflow provider-agnostic; swap in the CLI/action for whichever of Render/Fly.io/Railway is actually used.

Secrets & environment: DATABASE_URL is read from the environment (app/core/config.py), never committed. In CI/production it's set as a repository secret / host environment variable. Locally it defaults to a SQLite file so the project runs with zero setup.

Section 4 — AI Reflection

See separate note — written after completing the above, from my actual process.

also add the frontend and tell me what to do in my local pc, what to install and everything else step by step from running alembc, unicorn, checking db, how to run on railways, what to check

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/3906f9b7-800f-4adf-83f6-d8b15cf862d2).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
