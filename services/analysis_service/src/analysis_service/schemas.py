import datetime as dt
from pydantic import BaseModel, Field


class CreateReportRequest(BaseModel):
    work_id: str
    student_id: str
    assignment_id: str
    submitted_at: dt.datetime
    file_id: str


class ReportSummary(BaseModel):
    id: str
    work_id: str
    status: str
    plagiarism: bool
    plagiarism_reason: str | None = None
    plagiarized_from_work_id: str | None = None
    plagiarized_from_student_id: str | None = None
    created_at: dt.datetime


class CreateReportResponse(BaseModel):
    report: ReportSummary


class ReportContent(BaseModel):
    report_id: str
    work_id: str
    created_at: dt.datetime
    status: str
    plagiarism: bool
    plagiarism_reason: str | None = None
    plagiarized_from_work_id: str | None = None
    plagiarized_from_student_id: str | None = None
    file_id: str
    file_sha256: str
    stats: dict = Field(default_factory=dict)
    top_words: list[dict] = Field(default_factory=list)
