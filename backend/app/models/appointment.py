import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.types import UTCDateTime


class AppointmentStatus(str, enum.Enum):
    BOOKED = "booked"
    CANCELLED = "cancelled"


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)

    slot_start = Column(UTCDateTime, nullable=False)
    slot_end = Column(UTCDateTime, nullable=False)

    status = Column(
        Enum(AppointmentStatus, native_enum=False, length=20),
        nullable=False,
        default=AppointmentStatus.BOOKED,
        server_default=AppointmentStatus.BOOKED.value,
    )
    cancellation_reason = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    doctor = relationship("Doctor", back_populates="appointments")
    patient = relationship("Patient", back_populates="appointments")

    __table_args__ = (
        # This is the actual race-condition guard: the database itself
        # refuses a second BOOKED row for the same doctor+slot, regardless
        # of what the application layer checked a moment earlier.
        # Partial index -> cancelled appointments don't block rebooking
        # the same slot.
        Index(
            "uq_doctor_slot_active",
            "doctor_id",
            "slot_start",
            unique=True,
            sqlite_where=(status == AppointmentStatus.BOOKED.value),
            postgresql_where=(status == AppointmentStatus.BOOKED.value),
        ),
    )
