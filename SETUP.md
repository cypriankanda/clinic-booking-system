# Clinic Booking — full setup guide (backend + frontend)

Two apps live in this repo:

```
backend/    FastAPI + SQLAlchemy REST API (your assessment code)
src/        React frontend (TanStack Start) that consumes the API
```

The frontend calls the API over HTTP only — no shared code, no shared database.
Anything you can do in the UI you can also do with `curl` against `/docs`.

---

## 0. What to install on your PC (once)

| Tool | Version | Check with | Notes |
| --- | --- | --- | --- |
| Python | 3.11+ | `python --version` | 3.13 works too |
| Node.js | 20+ | `node --version` | for the frontend |
| npm | comes with Node | `npm --version` | bundled with Node.js |
| Docker Desktop | latest | `docker --version` | optional — only for the Postgres path |
| Git | any | `git --version` | |

On Windows use PowerShell and replace `source venv/bin/activate` with
`venv\Scripts\Activate.ps1`.

Deployment (Section 4) is done through the Render dashboard, not a CLI —
nothing extra to install there.

---

## 1. Backend — SQLite path (fastest, zero services)

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create your env file (optional — everything has sane defaults):

```bash
cp .env.example .env
# leave DATABASE_URL commented out to use SQLite (./clinic.db)
# ALLOWED_ORIGINS must include the frontend origin: http://localhost:8080
```

Create the schema. Two options — pick one:

**A. Alembic migrations (what you'd use in production)**

```bash
alembic revision --autogenerate -m "initial schema"   # first time only
alembic upgrade head
```

- `alembic revision --autogenerate` inspects `app/models/*` against the DB and
  writes a migration into `migrations/versions/`.
- `alembic upgrade head` applies every pending migration.
- `alembic current` shows which revision the DB is on; `alembic history` lists all.
- `alembic downgrade -1` rolls back one step.
- `migrations/env.py` reads `DATABASE_URL` from `app/core/config.py`, so the same
  commands work against SQLite locally and Postgres on Render. Nothing secret
  is stored in `alembic.ini`.

**B. Skip Alembic** — `app/main.py` runs `Base.metadata.create_all()` on startup,
so simply booting the API creates the tables. Fine for local dev and the
assessment; Alembic is the honest answer for production.

Seed the demo data (5 doctors Mon–Fri 09:00–17:00 UTC, 2 patients):

```bash
python seed.py     # safe to re-run; skips if doctors already exist
```

Run the API:

```bash
uvicorn app.main:app --reload --port 8000
```

Check it:

```bash
curl http://localhost:8000/health                       # {"status":"ok"}
curl http://localhost:8000/doctors                      # 5 doctors
curl "http://localhost:8000/doctors/1/availability?date=2026-08-21"
open http://localhost:8000/docs                          # Swagger UI
```

Run the tests (19, including the real two-thread double-booking race):

```bash
pytest -q
ruff check .
```

### Inspecting the SQLite database

```bash
sqlite3 backend/clinic.db ".tables"
sqlite3 backend/clinic.db "select id, name from doctors;"
sqlite3 backend/clinic.db "select id, doctor_id, slot_start, status from appointments;"
```

Reset everything: `rm backend/clinic.db` then re-run the schema + seed steps.

---

## 2. Backend — Postgres path (matches production)

```bash
cd backend
docker compose up --build
```

That starts Postgres + the API on `http://localhost:8000` and seeds it.

To point a local (non-Docker) API at Docker's Postgres instance instead, put
this in `.env`:

```
DATABASE_URL=postgresql+psycopg2://clinic:clinic@localhost:5432/clinic
```

then `alembic upgrade head && python seed.py && uvicorn app.main:app --reload`.

Inspect the Postgres DB:

```bash
docker compose exec db psql -U clinic -d clinic -c "\dt"
docker compose exec db psql -U clinic -d clinic -c "select * from appointments;"
```

---

## 3. Frontend

From the repo root (a separate terminal — keep uvicorn running):

```bash
npm install
cp .env.example .env # VITE_API_URL=http://localhost:8000
npm run dev
```

Open `http://localhost:8080`.

The header shows a live API status dot. Green = the frontend reached
`/health`. Red means uvicorn isn't running, the port is wrong, or CORS is
blocking you (see troubleshooting).

What the UI does:

- **Doctor / Patient / Date pickers** → `GET /doctors`, `GET /patients`
- **Available slots grid** → `GET /doctors/{id}/availability?date=…`
- **Click a slot** → `POST /appointments`
- **Upcoming appointments** → `GET /patients/{id}/appointments`
- **Cancel** (reason required) → `PATCH /appointments/{id}/cancel`
- **Reschedule** (pick a new slot) → `PATCH /appointments/{id}/reschedule`

All times are rendered in **UTC** to match the API contract exactly, so what you
see in the UI is literally what's stored.

Errors from the API (`409 SLOT_ALREADY_BOOKED`, validation failures, …) surface
as toasts using the API's own `error` code and `message`, so the UI never
invents its own wording.

Build check before deploying: `npm run build`. This produces a Nitro
build — the output you'll deploy is `.output/public` (static client
assets), with `.output/server` alongside it if you ever move off a
pure static-site deploy.

### Backend changes made for the frontend

- `GET /doctors` and `GET /patients` list endpoints (read-only) — the UI needs
  IDs to build its pickers, and hardcoding `doctor_id=1` would have been fake.
- CORS middleware, driven by `ALLOWED_ORIGINS`. Browsers block cross-origin
  calls without it; `curl` doesn't, which is why the API "worked" before.
- Alembic scaffolding (`alembic.ini`, `migrations/`).

---

## 4. Deploying to Render

Deployed live at:
- API: https://clinic-booking-api-9ttn.onrender.com
- Frontend: https://clinic-booking-frontend-thxz.onrender.com

### Backend (Web Service)

1. Render dashboard → **New → Web Service** → connect this GitHub repo,
   root directory `backend/`.
2. Add the database first: **New → PostgreSQL** (free tier). Once created,
   Render gives you an **Internal Database URL** — use that (not the external
   one) for services in the same Render project, since internal traffic is
   faster and doesn't count against external bandwidth.
3. Set environment variables on the API service (dashboard → Environment):
   - `DATABASE_URL` = the Postgres internal connection string, with the scheme
     changed to `postgresql+psycopg2://…`. Render gives you `postgresql://…`,
     which SQLAlchemy accepts but won't pin the driver; being explicit avoids
     surprises.
   - `ALLOWED_ORIGINS` = `https://clinic-booking-frontend-thxz.onrender.com`
   - `ENVIRONMENT` = `production`
4. **Build command:** `pip install -r requirements.txt`
5. **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
   Binding `0.0.0.0` and Render's `$PORT` is required — `localhost:8000` fails
   health checks.
6. **Release command** (runs before each new instance takes traffic):
   `alembic upgrade head` — so every deploy migrates first, and a bad
   migration blocks the deploy instead of shipping half-migrated.
7. **Health check path:** `/health`.
8. Deploy. Once live, seed the demo data once via the Render **Shell** tab on
   the service:
   ```bash
   python seed.py
   ```
9. Verify: `curl https://clinic-booking-api-9ttn.onrender.com/health` and open
   `/docs`.

### Frontend (Static Site)

1. Render dashboard → **New → Static Site** → connect the same repo, root
   directory `/` (repo root).
2. **Build command:** `npm install && npm run build`
3. **Publish directory:** `.output/public` — this is Nitro's static output
   folder (confirmed from the actual build log: `.output/nitro.json` +
   `.output/public`).
4. Environment variable: `VITE_API_URL` =
   `https://clinic-booking-api-9ttn.onrender.com` (no trailing slash) — this
   is baked in at build time, so changing it later requires a rebuild, not
   just a redeploy.
5. Auto-deploy on push to `main` is on by default for both services — they
   deploy independently of each other since they have separate build steps.

### What to check after deploying

- `GET /health` returns 200 over HTTPS.
- `GET /doctors` returns 5 doctors (proves migrations + seed ran).
- Book a slot from the deployed frontend; reload — it persists (proves
  Postgres, not an ephemeral SQLite file that dies on redeploy).
- Browser devtools → Network shows no CORS errors.
- Render logs (dashboard → Logs tab) are free of tracebacks on startup.
- Try booking the same slot twice → `409` with `SLOT_ALREADY_BOOKED`.
- Add `DEPLOY_HOOK_URL` as a GitHub secret (Render service → Settings →
  Deploy Hook → copy URL) so `.github/workflows/ci-cd.yml` can trigger a
  deploy on merge to `main`, independent of Render's own auto-deploy.

### Rollback

Render keeps previous deploys per service — roll back instantly from the
service's **Events** tab in the dashboard without touching git, or revert the
merge commit on `main` and let the pipeline redeploy the previous state.

---

## 5. Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| UI says "API unreachable" | uvicorn not running, or `VITE_API_URL` wrong. `curl http://localhost:8000/health` first. |
| Browser console: blocked by CORS policy | Add the frontend origin to `ALLOWED_ORIGINS` in `backend/.env` (or the Render environment variable), restart/redeploy. |
| `no such table: doctors` | Schema not created — run `alembic upgrade head` (or just start the API), then `python seed.py`. |
| Empty slot grid all day | It's a weekend (doctors work Mon–Fri), the day is fully booked, or every remaining slot is inside the 1-hour notice window. Try tomorrow's date. |
| `422` on booking | `slot_start` must be timezone-aware ISO 8601 on a :00/:30 boundary. The UI only ever sends values the API handed back. |
| `Target database is not up to date` (Alembic) | Run `alembic upgrade head` before `alembic revision --autogenerate`. |
| `psycopg2` install fails | Use `psycopg2-binary` (already pinned) and make sure the venv is active. |
| Render health check fails | Start command must use `--host 0.0.0.0 --port $PORT`. |
| Render free-tier service is slow to respond first request | Free web services spin down after inactivity; the first request after idle can take ~30-60s to wake it up. |