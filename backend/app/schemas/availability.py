from datetime import datetime

from pydantic import BaseModel


class AvailabilityResponse(BaseModel):
    doctor_id: int
    date: str
    available_slots: list[datetime]
