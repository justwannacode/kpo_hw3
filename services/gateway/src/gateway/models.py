import datetime as dt
from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


class Work(Base):
    __tablename__ = "works"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    assignment_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    submitted_at: Mapped[dt.datetime] = mapped_column(DateTime, default=lambda: dt.datetime.utcnow(), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String, nullable=False, default="CREATED")

    file_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    file_sha256: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    last_report_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    error: Mapped[str | None] = mapped_column(Text, nullable=True)
