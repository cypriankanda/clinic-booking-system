from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.exceptions import ConflictError, NotFoundError, ValidationFailedError
from app.models.appointment import Appointment, AppointmentStatus
from app.repositories.appointment_repo import AppointmentRepository
from app.repositories.doctor_repo import DoctorRepository
from app.repositories.patient_repo import PatientRepository

SLOT_MINUTES = settings.slot_duration_minutes
MIN_NOTICE = timedelta(minutes=settings.min_booking_notice_minutes)


class BookingService:
    """
    Owns every business rule for the clinic booking domain. Routers only
    translate HTTP <-> service calls; repositories only run queries. This
    class is where validation, slot math, and concurrency handling live.
    """

    def __init__(self, db: Session):
        self.db = db
        self.appointments = AppointmentRepository(db)
        self.doctors = DoctorRepository(db)
        self.patients = PatientRepository(db)

    # ---------- shared validation ----------

    def _get_doctor_or_404(self, doctor_id: int):
        doctor = self.doctors.get_by_id(doctor_id)
        if doctor is None:
            raise NotFoundError(f"Doctor {doctor_id} not found")
        return doctor

    def _get_patient_or_404(self, patient_id: int):
        patient = self.patients.get_by_id(patient_id)
        if patient is None:
            raise NotFoundError(f"Patient {patient_id} not found")
        return patient

    def _get_appointment_or_404(self, appointment_id: int) -> Appointment:
        appointment = self.appointments.get_by_id(appointment_id)
        if appointment is None:
            raise NotFoundError(f"Appointment {appointment_id} not found")
        return appointment

    def _validate_slot(
        self, doctor_id: int, slot_start: datetime, *, enforce_notice: bool
    ) -> datetime:
        """
        Validates that slot_start is:
          - timezone-aware (already enforced by the Pydantic schema, checked
            again here since this is the real trust boundary)
          - aligned to the slot grid (on a 30-minute boundary)
          - not in the past
          - not inside the minimum-notice buffer (bonus requirement),
            when enforce_notice is True
          - within the doctor's working hours for that weekday

        Returns slot_end for convenience.
        """
        if slot_start.tzinfo is None:
            raise ValidationFailedError("slot_start must be timezone-aware")

        slot_start = slot_start.astimezone(timezone.utc)
        now = datetime.now(timezone.utc)

        if slot_start < now:
            raise ValidationFailedError("Cannot book a slot in the past")

        if enforce_notice and slot_start < now + MIN_NOTICE:
            raise ValidationFailedError(
                f"Bookings must be made at least {settings.min_booking_notice_minutes} "
                "minutes in advance"
            )

        if slot_start.second != 0 or slot_start.microsecond != 0 or (
            slot_start.minute % SLOT_MINUTES != 0
        ):
            raise ValidationFailedError(
                f"slot_start must align to {SLOT_MINUTES}-minute boundaries"
            )

        working_hours = self.doctors.get_working_hours(doctor_id, slot_start.weekday())
        if working_hours is None:
            raise ValidationFailedError("Doctor does not work on this day")

        slot_end = slot_start + timedelta(minutes=SLOT_MINUTES)
        day_start = datetime.combine(
            slot_start.date(), working_hours.start_time, tzinfo=timezone.utc
        )
        day_end = datetime.combine(
            slot_start.date(), working_hours.end_time, tzinfo=timezone.utc
        )
        if slot_start < day_start or slot_end > day_end:
            raise ValidationFailedError(
                f"Slot must fall within working hours "
                f"({working_hours.start_time}-{working_hours.end_time})"
            )

        return slot_end

    # ---------- booking ----------

    def book_appointment(
        self, doctor_id: int, patient_id: int, slot_start: datetime
    ) -> Appointment:
        self._get_doctor_or_404(doctor_id)
        self._get_patient_or_404(patient_id)
        slot_end = self._validate_slot(doctor_id, slot_start, enforce_notice=True)
        slot_start = slot_start.astimezone(timezone.utc)

        # Optimistic pre-check: gives a fast, friendly 409 in the common case
        # without waiting on a DB round trip failure. This is NOT the safety
        # guarantee -- it can't be, under concurrent requests. The real
        # guarantee is the partial unique index on (doctor_id, slot_start)
        # WHERE status='booked', enforced below.
        if self.appointments.get_active_for_doctor_and_slot(doctor_id, slot_start):
            raise ConflictError("This slot is already booked")

        appointment = Appointment(
            doctor_id=doctor_id,
            patient_id=patient_id,
            slot_start=slot_start,
            slot_end=slot_end,
            status=AppointmentStatus.BOOKED,
        )
        try:
            self.appointments.add(appointment)
            self.db.commit()
        except IntegrityError:
            # Two requests raced past the pre-check above; the database's
            # unique index is what actually decided the winner. Whoever
            # lands here lost the race and gets a clean 409.
            self.db.rollback()
            raise ConflictError("This slot was just booked by another patient")

        self.db.refresh(appointment)
        return appointment

    # ---------- cancel ----------

    def cancel_appointment(self, appointment_id: int, reason: str) -> Appointment:
        appointment = self._get_appointment_or_404(appointment_id)
        if appointment.status == AppointmentStatus.CANCELLED:
            raise ConflictError("Appointment is already cancelled")

        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancellation_reason = reason
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    # ---------- reschedule ----------

    def reschedule_appointment(self, appointment_id: int, new_slot_start: datetime) -> Appointment:
        appointment = self._get_appointment_or_404(appointment_id)
        if appointment.status == AppointmentStatus.CANCELLED:
            raise ConflictError("Cannot reschedule a cancelled appointment")

        new_slot_end = self._validate_slot(
            appointment.doctor_id, new_slot_start, enforce_notice=True
        )
        new_slot_start = new_slot_start.astimezone(timezone.utc)

        existing = self.appointments.get_active_for_doctor_and_slot(
            appointment.doctor_id, new_slot_start
        )
        if existing and existing.id != appointment.id:
            raise ConflictError("This slot is already booked")

        # Updating slot_start/slot_end on the SAME row -- rather than
        # cancel+recreate -- makes the "free the old slot, claim the new
        # one" operation a single atomic UPDATE. The old slot is freed and
        # the new one claimed in one statement; the unique index still
        # protects against a concurrent booking of the new slot.
        appointment.slot_start = new_slot_start
        appointment.slot_end = new_slot_end
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("This slot was just booked by another patient")

        self.db.refresh(appointment)
        return appointment

    # ---------- availability ----------

    def get_availability(self, doctor_id: int, date_: datetime) -> list[datetime]:
        self._get_doctor_or_404(doctor_id)

        working_hours = self.doctors.get_working_hours(doctor_id, date_.weekday())
        if working_hours is None:
            return []

        day_start = datetime.combine(date_.date(), working_hours.start_time, tzinfo=timezone.utc)
        day_end = datetime.combine(date_.date(), working_hours.end_time, tzinfo=timezone.utc)

        booked = self.appointments.list_booked_for_doctor_on_date(doctor_id, day_start, day_end)
        booked_starts = {a.slot_start for a in booked}

        now = datetime.now(timezone.utc)
        earliest_bookable = now + MIN_NOTICE

        slots = []
        cursor = day_start
        step = timedelta(minutes=SLOT_MINUTES)
        while cursor + step <= day_end:
            if cursor not in booked_starts and cursor >= earliest_bookable:
                slots.append(cursor)
            cursor += step
        return slots

    # ---------- bonus: patient appointment list ----------

    def list_patient_appointments(self, patient_id: int) -> list[Appointment]:
        self._get_patient_or_404(patient_id)
        return self.appointments.list_upcoming_for_patient(patient_id)
