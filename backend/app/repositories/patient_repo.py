
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.patient import Patient


class PatientRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, patient_id: int) -> Patient | None:
        return self.db.get(Patient, patient_id)

    def list_all(self) -> list[Patient]:
        return list(self.db.execute(select(Patient).order_by(Patient.name)).scalars())
