import hashlib
from pathlib import Path
from fastapi import UploadFile

CHUNK_SIZE = 1024 * 1024  # 1MB


async def save_upload_file(upload_file: UploadFile, destination: Path) -> tuple[int, str]:
    """Сохранить и посчитать sha256."""
    destination.parent.mkdir(parents=True, exist_ok=True)

    hasher = hashlib.sha256()
    size = 0

    with destination.open("wb") as out:
        while True:
            chunk = await upload_file.read(CHUNK_SIZE)
            if not chunk:
                break
            size += len(chunk)
            hasher.update(chunk)
            out.write(chunk)

    await upload_file.close()
    return size, hasher.hexdigest()
