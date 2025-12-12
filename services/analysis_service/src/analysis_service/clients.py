from __future__ import annotations

import httpx
from .config import settings


class FileServiceUnavailable(RuntimeError):
    pass


async def get_file_meta(file_id: str) -> dict:
    url = f"{settings.file_service_url.rstrip('/')}/files/{file_id}/meta"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
        if resp.status_code == 404:
            raise FileNotFoundError("File not found")
        resp.raise_for_status()
        return resp.json()
    except (httpx.ConnectError, httpx.ReadTimeout) as e:
        raise FileServiceUnavailable(str(e))


async def download_file_bytes(file_id: str) -> bytes:
    url = f"{settings.file_service_url.rstrip('/')}/files/{file_id}/download"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
        if resp.status_code == 404:
            raise FileNotFoundError("File not found")
        resp.raise_for_status()
        return resp.content
    except (httpx.ConnectError, httpx.ReadTimeout) as e:
        raise FileServiceUnavailable(str(e))
