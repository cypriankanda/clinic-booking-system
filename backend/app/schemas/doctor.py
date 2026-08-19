from datetime import time

from pydantic import BaseModel, ConfigDict


class WorkingHoursOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day_of_week: int
    start_time: time
    end_time: time


class DoctorOut(BaseModel):
    """Read model for the doctor list the frontend renders in its picker."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    specialty: str | None = None
    working_hours: list[WorkingHoursOut] = []
