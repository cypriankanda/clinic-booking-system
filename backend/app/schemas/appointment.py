from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.appointment import AppointmentStatus


class AppointmentCreate(BaseModel):
    doctor_id: int
    patient_id: int
    slot_start: datetime = Field(..., description="Start of the 30-minute slot, ISO 8601, UTC")

    @field_validator("slot_start")
    @classmethod
    def must_be_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("slot_start must include a timezone (use UTC, e.g. ...Z)")
        return v


class AppointmentReschedule(BaseModel):
    slot_start: datetime = Field(..., description="New start time for the appointment")

    @field_validator("slot_start")
    @classmethod
    def must_be_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("slot_start must include a timezone (use UTC, e.g. ...Z)")
        return v


class AppointmentCancel(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doctor_id: int
    patient_id: int
    slot_start: datetime
    slot_end: datetime
    status: AppointmentStatus
    cancellation_reason: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
