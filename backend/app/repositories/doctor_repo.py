
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.doctor import Doctor, WorkingHours


class DoctorRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, doctor_id: int) -> Doctor | None:
        return self.db.get(Doctor, doctor_id)

    def get_working_hours(self, doctor_id: int, day_of_week: int) -> WorkingHours | None:
        stmt = select(WorkingHours).where(
            WorkingHours.doctor_id == doctor_id,
            WorkingHours.day_of_week == day_of_week,
        )
        return self.db.execute(stmt).scalar_one_or_none()
