from __future__ import annotations

import httpx
from fastapi import UploadFile
from .config import settings


class ServiceUnavailable(RuntimeError):
    pass


async def store_file(file: UploadFile) -> dict:
    url = f"{settings.file_service_url.rstrip('/')}/files"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            files = {"file": (file.filename or "uploaded.bin", file.file, file.content_type or "application/octet-stream")}
            resp = await client.post(url, files=files)
        resp.raise_for_status()
        return resp.json()
    except (httpx.ConnectError, httpx.ReadTimeout) as e:
        raise ServiceUnavailable(f"File service unavailable: {e}")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"File service error {e.response.status_code}: {e.response.text}")


async def create_report(payload: dict) -> dict:
    url = f"{settings.analysis_service_url.rstrip('/')}/reports"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()
    except (httpx.ConnectError, httpx.ReadTimeout) as e:
        raise ServiceUnavailable(f"Analysis service unavailable: {e}")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Analysis service error {e.response.status_code}: {e.response.text}")


async def list_reports(work_id: str) -> list[dict]:
    url = f"{settings.analysis_service_url.rstrip('/')}/works/{work_id}/reports"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()
    except (httpx.ConnectError, httpx.ReadTimeout) as e:
        raise ServiceUnavailable(f"Analysis service unavailable: {e}")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Analysis service error {e.response.status_code}: {e.response.text}")
