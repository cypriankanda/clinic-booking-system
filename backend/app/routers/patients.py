
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.appointment import AppointmentOut
from app.schemas.patient import PatientOut
from app.services.booking_service import BookingService

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=list[PatientOut])
def list_patients(db: Session = Depends(get_db)):
    service = BookingService(db)
    return service.list_patients()


@router.get("/{patient_id}/appointments", response_model=list[AppointmentOut])
def list_patient_appointments(patient_id: int, db: Session = Depends(get_db)):
    service = BookingService(db)
    return service.list_patient_appointments(patient_id)
