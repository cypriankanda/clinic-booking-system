from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401  -- ensures models are registered on Base
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

register_error_handlers(app)

app.include_router(appointments.router)
app.include_router(doctors.router)
app.include_router(patients.router)


@app.get("/health", tags=["meta"])
def health_check():
    return {"status": "ok"}
