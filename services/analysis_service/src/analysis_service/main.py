import json
import uuid
from pathlib import Path

import httpx
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from .config import settings
from .db import SessionLocal, init_db
from .models import Work, Report
from .schemas import (
    CreateReportRequest,
    CreateReportResponse,
    ReportSummary,
    ReportContent,
)
from .clients import get_file_meta, download_file_bytes, FileServiceUnavailable
from .analyzer import extract_words, top_words

app = FastAPI(title="File Analysis Service", version="1.0.0")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def _startup():
    Path(settings.reports_dir).mkdir(parents=True, exist_ok=True)
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


def _report_summary(r: Report) -> ReportSummary:
    return ReportSummary(
        id=r.id,
        work_id=r.work_id,
        status=r.status,
        plagiarism=r.plagiarism,
        plagiarism_reason=r.plagiarism_reason,
        plagiarized_from_work_id=r.plagiarized_from_work_id,
        plagiarized_from_student_id=r.plagiarized_from_student_id,
        created_at=r.created_at,
    )


@app.post("/reports", response_model=CreateReportResponse)
async def create_report(req: CreateReportRequest, db: Session = Depends(get_db)):
    # 1) Получаем sha256 у File Service (он отвечает за подсчёт хеша при загрузке)
    try:
        meta = await get_file_meta(req.file_id)
    except FileServiceUnavailable as e:
        raise HTTPException(status_code=503, detail=f"File service unavailable: {e}")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found in file service")

    file_sha256 = meta["sha256"]

    # 2) Upsert Work (храним копию метаданных для поиска ранних сдач)
    work = db.get(Work, req.work_id)
    if not work:
        work = Work(
            id=req.work_id,
            student_id=req.student_id,
            assignment_id=req.assignment_id,
            submitted_at=req.submitted_at,
            file_id=req.file_id,
            file_sha256=file_sha256,
        )
        db.add(work)
        db.commit()
        db.refresh(work)
    else:
        # если повторный анализ — обновим поля, если они поменялись
        work.student_id = req.student_id
        work.assignment_id = req.assignment_id
        work.submitted_at = req.submitted_at
        work.file_id = req.file_id
        work.file_sha256 = file_sha256
        db.commit()
        db.refresh(work)

    # 3) Детект «плагиата» = есть более ранняя сдача другим студентом с тем же sha256
    earlier = db.execute(
        select(Work)
        .where(
            and_(
                Work.file_sha256 == file_sha256,
                Work.submitted_at < req.submitted_at,
                Work.student_id != req.student_id,
            )
        )
        .order_by(Work.submitted_at.asc())
        .limit(1)
    ).scalar_one_or_none()

    plagiarism = earlier is not None
    plagiarism_reason = None
    plag_from_work_id = None
    plag_from_student_id = None
    if plagiarism:
        plagiarism_reason = "Earlier identical submission exists (same sha256)."
        plag_from_work_id = earlier.id
        plag_from_student_id = earlier.student_id

    # 4) (опционально) небольшой текстовый анализ: топ слов, если файл читается как текст
    stats = {}
    top = []
    try:
        raw = await download_file_bytes(req.file_id)
        text = raw.decode("utf-8", errors="ignore")
        words = extract_words(text)
        stats = {
            "bytes": len(raw),
            "approx_chars": len(text),
            "words": len(words),
        }
        top = top_words(words, limit=30)
    except FileServiceUnavailable:
        # не валим весь отчёт: сохраняем отчёт, но без статистики/топ-слов
        stats = {"warning": "file_service_unavailable_for_text_analysis"}
    except Exception:
        stats = {"warning": "failed_to_parse_text"}

    report_id = str(uuid.uuid4())
    report_path = Path(settings.reports_dir) / f"{report_id}.json"

    # 5) Запись в БД + JSON-файл отчёта на диск
    record = Report(
        id=report_id,
        work_id=req.work_id,
        status="COMPLETED",
        plagiarism=plagiarism,
        plagiarism_reason=plagiarism_reason,
        plagiarized_from_work_id=plag_from_work_id,
        plagiarized_from_student_id=plag_from_student_id,
        report_path=str(report_path),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # теперь created_at уже известен
    content = ReportContent(
        report_id=report_id,
        work_id=req.work_id,
        created_at=record.created_at,  # <-- ВОТ ЭТО главное
        status=record.status,
        plagiarism=record.plagiarism,
        plagiarism_reason=record.plagiarism_reason,
        plagiarized_from_work_id=record.plagiarized_from_work_id,
        plagiarized_from_student_id=record.plagiarized_from_student_id,
        file_id=req.file_id,
        file_sha256=file_sha256,
        stats=stats,
        top_words=top,
    )

    report_path.write_text(content.model_dump_json(indent=2), encoding="utf-8")
    return CreateReportResponse(report=_report_summary(record))


@app.get("/works/{work_id}/reports", response_model=list[ReportSummary])
def list_reports_for_work(work_id: str, db: Session = Depends(get_db)):
    rows = db.execute(select(Report).where(Report.work_id == work_id).order_by(Report.created_at.desc())).scalars().all()
    return [_report_summary(r) for r in rows]


@app.get("/reports/{report_id}", response_model=ReportContent)
def get_report_content(report_id: str, db: Session = Depends(get_db)):
    r = db.get(Report, report_id)
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    path = Path(r.report_path)
    if not path.exists():
        raise HTTPException(status_code=410, detail="Report metadata exists but report file is missing")
    return ReportContent(**json.loads(path.read_text(encoding="utf-8")))


@app.get("/reports/{report_id}/download")
def download_report(report_id: str, db: Session = Depends(get_db)):
    r = db.get(Report, report_id)
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    path = Path(r.report_path)
    if not path.exists():
        raise HTTPException(status_code=410, detail="Report file missing")
    return FileResponse(str(path), media_type="application/json", filename=f"{report_id}.json")


@app.get("/reports/{report_id}/wordcloud")
async def wordcloud(report_id: str, db: Session = Depends(get_db)):
    """Возвращает PNG облака слов через quickchart.io (опциональная фича)."""
    r = db.get(Report, report_id)
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")

    # Берём текст напрямую из файла, чтобы не зависеть от формата исходного файла
    path = Path(r.report_path)
    if not path.exists():
        raise HTTPException(status_code=410, detail="Report file missing")
    data = json.loads(path.read_text(encoding="utf-8"))
    words = data.get("top_words") or []
    if not words:
        raise HTTPException(status_code=422, detail="Not enough text to build wordcloud")

    # quickchart принимает текст, можно повторить слова count раз
    # чтобы размеры облака соответствовали частотам
    text = []
    for item in words:
        w = item.get("word")
        n = int(item.get("count", 1))
        text.append((" " + w) * min(n, 10))  # ограничим повторения
    text = " ".join(text).strip()

    payload = {
        "format": "png",
        "width": 800,
        "height": 500,
        "removeStopwords": True,
        "text": text,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post("https://quickchart.io/wordcloud", json=payload)
        resp.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"QuickChart unavailable: {e}")

    return Response(content=resp.content, media_type="image/png")
