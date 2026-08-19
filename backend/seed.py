"""
Populates the database with 5 doctors (Mon-Fri, 09:00-17:00) and a couple of
sample patients, so the API is immediately usable after `docker-compose up`
or a local run. Safe to re-run -- it skips seeding if doctors already exist.

Usage: python seed.py
"""
from datetime import time

from app.core.database import Base, engine, SessionLocal
from app import models
from app.models.doctor import Doctor, WorkingHours
from app.models.patient import Patient

Base.metadata.create_all(bind=engine)

DOCTOR_NAMES = [
    "Dr. Amina Yusuf",
    "Dr. Brian Otieno",
    "Dr. Wanjiru Kamau",
    "Dr. Peter Mwangi",
    "Dr. Grace Achieng",
]

PATIENTS = [
    ("John Kariuki", "john.kariuki@example.com"),
    ("Mary Njeri", "mary.njeri@example.com"),
]


def seed():
    db = SessionLocal()
    try:
        if db.query(Doctor).count() > 0:
            print("Doctors already exist -- skipping seed.")
            return

        for name in DOCTOR_NAMES:
            doctor = Doctor(name=name)
            db.add(doctor)
            db.flush()  # get doctor.id
            for day in range(0, 5):  # Monday-Friday
                db.add(
                    WorkingHours(
                        doctor_id=doctor.id,
                        day_of_week=day,
                        start_time=time(9, 0),
                        end_time=time(17, 0),
                    )
                )

        for name, email in PATIENTS:
            db.add(Patient(name=name, email=email))

        db.commit()
        print(f"Seeded {len(DOCTOR_NAMES)} doctors and {len(PATIENTS)} patients.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
