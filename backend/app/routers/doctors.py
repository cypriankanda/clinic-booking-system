from datetime import date as date_type
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.exceptions import ValidationFailedError
from app.schemas.availability import AvailabilityResponse
from app.services.booking_service import BookingService

router = APIRouter(prefix="/doctors", tags=["doctors"])


@router.get("/{doctor_id}/availability", response_model=AvailabilityResponse)
def get_availability(
    doctor_id: int,
    date: str = Query(..., description="Date to check, YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    try:
        parsed_date = date_type.fromisoformat(date)
    except ValueError:
        raise ValidationFailedError("date must be in YYYY-MM-DD format")

    service = BookingService(db)
    slots = service.get_availability(
        doctor_id, datetime.combine(parsed_date, datetime.min.time(), tzinfo=timezone.utc)
    )
    return AvailabilityResponse(doctor_id=doctor_id, date=date, available_slots=slots)
