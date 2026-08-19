from pydantic import BaseModel, ConfigDict


class PatientOut(BaseModel):
    """Read model for the patient picker in the frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
