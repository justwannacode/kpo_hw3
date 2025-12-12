import datetime as dt
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


class Work(Base):
    __tablename__ = "works"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    assignment_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    submitted_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, index=True)

    file_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    file_sha256: Mapped[str] = mapped_column(String, nullable=False, index=True)

    reports: Mapped[list["Report"]] = relationship(back_populates="work")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    work_id: Mapped[str] = mapped_column(String, ForeignKey("works.id"), nullable=False, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=lambda: dt.datetime.utcnow(), nullable=False)

    status: Mapped[str] = mapped_column(String, nullable=False)  # COMPLETED / FAILED
    plagiarism: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    plagiarism_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    plagiarized_from_work_id: Mapped[str | None] = mapped_column(String, nullable=True)
    plagiarized_from_student_id: Mapped[str | None] = mapped_column(String, nullable=True)

    report_path: Mapped[str] = mapped_column(String, nullable=False)

    work: Mapped[Work] = relationship(back_populates="reports")
