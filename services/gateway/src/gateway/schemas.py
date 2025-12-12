import datetime as dt
from pydantic import BaseModel


class WorkOut(BaseModel):
    id: str
    student_id: str
    assignment_id: str
    submitted_at: dt.datetime
    status: str
    file_id: str | None = None
    file_sha256: str | None = None
    last_report_id: str | None = None
    error: str | None = None


class ReportSummary(BaseModel):
    id: str
    work_id: str
    status: str
    plagiarism: bool
    plagiarism_reason: str | None = None
    plagiarized_from_work_id: str | None = None
    plagiarized_from_student_id: str | None = None
    created_at: dt.datetime


class SubmitWorkResponse(BaseModel):
    work: WorkOut
    report: ReportSummary | None = None
