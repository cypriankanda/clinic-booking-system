from sqlalchemy import Column, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    specialty = Column(String(120), nullable=True)  # nullable now; room to grow

    working_hours = relationship(
        "WorkingHours", back_populates="doctor", cascade="all, delete-orphan"
    )
    appointments = relationship("Appointment", back_populates="doctor")


class WorkingHours(Base):
    """
    A doctor's recurring weekly availability window, e.g. Mon 09:00-17:00.
    Slots are derived from this at read time, not pre-generated and stored —
    see README for the reasoning.
    """

    __tablename__ = "working_hours"
    __table_args__ = (
        UniqueConstraint("doctor_id", "day_of_week", name="uq_doctor_day"),
    )

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday ... 6=Sunday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    doctor = relationship("Doctor", back_populates="working_hours")
