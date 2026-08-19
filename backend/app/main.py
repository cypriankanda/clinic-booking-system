from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  -- ensures models are registered on Base
from app.core.config import settings
from app.core.database import Base, engine
from app.error_handlers import register_error_handlers
from app.routers import appointments, doctors, patients


@asynccontextmanager
async def lifespan(app: FastAPI):
    # For this take-home, tables are created directly from the models at
    # startup rather than via Alembic migrations -- a reasonable trade-off
    # given the assessment's time box. In a real production setup this
    # would be replaced by `alembic upgrade head` run as a release step
    # (see README).
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Clinic Booking API",
    description="Backend take-home assessment - Savannah Informatics",
    version="1.0.0",
    lifespan=lifespan,
)

# The React frontend runs on a different origin in development, so the
# browser needs explicit CORS permission. ALLOWED_ORIGINS is a comma-separated
# env var in production (e.g. your deployed frontend URL).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_origin_regex=r"https://.*\.lovable\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

app.include_router(appointments.router)
app.include_router(doctors.router)
app.include_router(patients.router)


@app.get("/health", tags=["meta"])
def health_check():
    return {"status": "ok"}
