import uuid
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from .db import SessionLocal, init_db
from .models import Work
from .schemas import WorkOut, SubmitWorkResponse, ReportSummary
from .clients import store_file, create_report, list_reports, ServiceUnavailable

app = FastAPI(title="API Gateway", version="1.0.0")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


def _work_out(w: Work) -> WorkOut:
    return WorkOut(
        id=w.id,
        student_id=w.student_id,
        assignment_id=w.assignment_id,
        submitted_at=w.submitted_at,
        status=w.status,
        file_id=w.file_id,
        file_sha256=w.file_sha256,
        last_report_id=w.last_report_id,
        error=w.error,
    )


@app.post("/works", response_model=SubmitWorkResponse)
async def submit_work(
    student_id: str = Form(...),
    assignment_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # фиксируем факт сдачи в БД gateway
    work_id = str(uuid.uuid4())
    work = Work(
        id=work_id,
        student_id=student_id,
        assignment_id=assignment_id,
        status="CREATED",
    )
    db.add(work)
    db.commit()
    db.refresh(work)

    # сохраняем файл через File Service
    try:
        file_resp = await store_file(file)
    except ServiceUnavailable as e:
        work.status = "FILE_STORE_FAILED"
        work.error = str(e)
        db.commit()
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        work.status = "FILE_STORE_FAILED"
        work.error = str(e)
        db.commit()
        raise HTTPException(status_code=502, detail=str(e))

    meta = file_resp["file"]
    work.file_id = meta["id"]
    work.file_sha256 = meta["sha256"]
    work.status = "FILE_STORED"
    db.commit()
    db.refresh(work)

    # запускаем анализ через Analysis Service
    report_summary = None
    payload = {
        "work_id": work.id,
        "student_id": work.student_id,
        "assignment_id": work.assignment_id,
        "submitted_at": work.submitted_at.isoformat(),
        "file_id": work.file_id,
    }

    try:
        rep = await create_report(payload)
        report_summary = rep["report"]
        work.last_report_id = report_summary["id"]
        work.status = "ANALYZED"
        work.error = None
        db.commit()
        db.refresh(work)
    except ServiceUnavailable as e:
        work.status = "ANALYSIS_FAILED"
        work.error = str(e)
        db.commit()
        # возвращаем work + 503
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        work.status = "ANALYSIS_FAILED"
        work.error = str(e)
        db.commit()
        raise HTTPException(status_code=502, detail=str(e))

    return SubmitWorkResponse(work=_work_out(work), report=ReportSummary(**report_summary))


@app.get("/works/{work_id}", response_model=WorkOut)
def get_work(work_id: str, db: Session = Depends(get_db)):
    work = db.get(Work, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    return _work_out(work)


@app.get("/works/{work_id}/reports")
async def get_reports(work_id: str, db: Session = Depends(get_db)):
    work = db.get(Work, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")

    try:
        reports = await list_reports(work_id)
        return {"work_id": work_id, "reports": reports}
    except ServiceUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/works/{work_id}/retry-analysis", response_model=SubmitWorkResponse)
async def retry_analysis(work_id: str, db: Session = Depends(get_db)):
    work = db.get(Work, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    if not work.file_id:
        raise HTTPException(status_code=409, detail="Work has no stored file_id; cannot analyze")

    payload = {
        "work_id": work.id,
        "student_id": work.student_id,
        "assignment_id": work.assignment_id,
        "submitted_at": work.submitted_at.isoformat(),
        "file_id": work.file_id,
    }

    try:
        rep = await create_report(payload)
        report_summary = rep["report"]
        work.last_report_id = report_summary["id"]
        work.status = "ANALYZED"
        work.error = None
        db.commit()
        db.refresh(work)
        return SubmitWorkResponse(work=_work_out(work), report=ReportSummary(**report_summary))
    except ServiceUnavailable as e:
        work.status = "ANALYSIS_FAILED"
        work.error = str(e)
        db.commit()
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        work.status = "ANALYSIS_FAILED"
        work.error = str(e)
        db.commit()
        raise HTTPException(status_code=502, detail=str(e))
