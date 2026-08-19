from pydantic import BaseModel, ConfigDict, EmailStr


class PatientCreate(BaseModel):
    name: str
    email: EmailStr


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
