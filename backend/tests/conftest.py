from datetime import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app
from app.models.doctor import Doctor, WorkingHours
from app.models.patient import Patient


@pytest.fixture()
def db_url(tmp_path):
    # A real file (not :memory:) so multiple connections -- as used by the
    # concurrency test -- see the same database.
    return f"sqlite:///{tmp_path}/test_clinic.db"


@pytest.fixture()
def engine(db_url):
    eng = create_engine(db_url, connect_args={"check_same_thread": False}, future=True)
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture()
def SessionLocal(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture()
def seeded_ids(SessionLocal):
    db = SessionLocal()
    doctor = Doctor(name="Dr. Test")
    db.add(doctor)
    db.flush()
    for day in range(5):
        db.add(
            WorkingHours(
                doctor_id=doctor.id, day_of_week=day, start_time=time(9, 0), end_time=time(17, 0)
            )
        )
    patient_a = Patient(name="Patient A", email="a@example.com")
    patient_b = Patient(name="Patient B", email="b@example.com")
    db.add_all([patient_a, patient_b])
    db.commit()
    ids = {"doctor_id": doctor.id, "patient_a_id": patient_a.id, "patient_b_id": patient_b.id}
    db.close()
    return ids


@pytest.fixture()
def client(SessionLocal):
    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
