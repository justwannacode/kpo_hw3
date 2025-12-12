import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal, init_db
from .models import StoredFile
from .schemas import UploadResponse, FileMeta
from .storage import save_upload_file

app = FastAPI(title="File Storing Service", version="1.0.0")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def _startup():
    Path(settings.files_dir).mkdir(parents=True, exist_ok=True)
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/files", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_id = str(uuid.uuid4())
    safe_name = (file.filename or "uploaded.bin").replace("/", "_").replace("\\", "_")
    stored_path = Path(settings.files_dir) / f"{file_id}__{safe_name}"

    try:
        size, sha256 = await save_upload_file(file, stored_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store file: {e}")

    record = StoredFile(
        id=file_id,
        original_filename=safe_name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        sha256=sha256,
        stored_path=str(stored_path),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return UploadResponse(
        file=FileMeta(
            id=record.id,
            original_filename=record.original_filename,
            content_type=record.content_type,
            size_bytes=record.size_bytes,
            sha256=record.sha256,
            created_at=record.created_at,
        )
    )


@app.get("/files/{file_id}/meta", response_model=FileMeta)
def get_file_meta(file_id: str, db: Session = Depends(get_db)):
    record = db.get(StoredFile, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    return FileMeta(
        id=record.id,
        original_filename=record.original_filename,
        content_type=record.content_type,
        size_bytes=record.size_bytes,
        sha256=record.sha256,
        created_at=record.created_at,
    )


@app.get("/files/{file_id}/download")
def download(file_id: str, db: Session = Depends(get_db)):
    record = db.get(StoredFile, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(record.stored_path)
    if not path.exists():
        raise HTTPException(status_code=410, detail="File metadata exists but file is missing on disk")

    return FileResponse(
        path=str(path),
        media_type=record.content_type,
        filename=record.original_filename,
    )
