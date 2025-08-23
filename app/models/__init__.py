from sqlalchemy import Column, String, Integer, Time, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
import uuid

from ..database import Base, engine, SessionLocal


class StoreTimezone(Base):
    __tablename__ = "store_timezones"

    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    timezone_str: Mapped[str] = mapped_column(String, nullable=False)


class StoreHours(Base):
    __tablename__ = "store_hours"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    dayOfWeek: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time_local: Mapped[str] = mapped_column(String, nullable=False)
    end_time_local: Mapped[str] = mapped_column(String, nullable=False)


class StoreStatus(Base):
    __tablename__ = "store_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    timestamp_utc: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReportJob(Base):
    __tablename__ = "report_jobs"

    report_id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False)  # "Running", "Complete", "Failed"
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    csv_data: Mapped[str] = mapped_column(Text, nullable=True)
    error_message: Mapped[str] = mapped_column(String, nullable=True)

