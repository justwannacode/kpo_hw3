import datetime as dt
from pydantic import BaseModel


class FileMeta(BaseModel):
    id: str
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    created_at: dt.datetime


class UploadResponse(BaseModel):
    file: FileMeta
