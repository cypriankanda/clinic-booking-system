from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.appointment import (
    AppointmentCancel,
    AppointmentCreate,
    AppointmentOut,
    AppointmentReschedule,
)
from app.services.booking_service import BookingService

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def book_appointment(payload: AppointmentCreate, db: Session = Depends(get_db)):
    service = BookingService(db)
    return service.book_appointment(
        doctor_id=payload.doctor_id,
        patient_id=payload.patient_id,
        slot_start=payload.slot_start,
    )


@router.patch("/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel_appointment(
    appointment_id: int, payload: AppointmentCancel, db: Session = Depends(get_db)
):
    service = BookingService(db)
    return service.cancel_appointment(appointment_id, payload.reason)


@router.patch("/{appointment_id}/reschedule", response_model=AppointmentOut)
def reschedule_appointment(
    appointment_id: int, payload: AppointmentReschedule, db: Session = Depends(get_db)
):
    service = BookingService(db)
    return service.reschedule_appointment(appointment_id, payload.slot_start)
