from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentStatus


class AppointmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, appointment_id: int) -> Appointment | None:
        return self.db.get(Appointment, appointment_id)

    def get_active_for_doctor_and_slot(
        self, doctor_id: int, slot_start: datetime
    ) -> Appointment | None:
        stmt = select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.slot_start == slot_start,
            Appointment.status == AppointmentStatus.BOOKED,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_booked_for_doctor_on_date(
        self, doctor_id: int, day_start: datetime, day_end: datetime
    ) -> list[Appointment]:
        stmt = select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.slot_start >= day_start,
            Appointment.slot_start < day_end,
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_upcoming_for_patient(self, patient_id: int) -> list[Appointment]:
        stmt = (
            select(Appointment)
            .where(
                Appointment.patient_id == patient_id,
                Appointment.status == AppointmentStatus.BOOKED,
                Appointment.slot_start >= datetime.now(timezone.utc),
            )
            .order_by(Appointment.slot_start.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def add(self, appointment: Appointment) -> Appointment:
        self.db.add(appointment)
        self.db.flush()  # surfaces IntegrityError here, inside the caller's transaction
        return appointment
