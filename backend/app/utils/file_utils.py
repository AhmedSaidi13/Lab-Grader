import uuid
import aiofiles
from pathlib import Path
from fastapi import UploadFile, HTTPException
from app.config import get_settings

settings = get_settings()


async def save_upload(
    file: UploadFile,
    subfolder: str,
    allowed_extensions: list[str] | None = None,
) -> tuple[str, str]:
    """
    Save an uploaded file to disk.
    Returns (file_path_str, original_filename).
    """
    if allowed_extensions:
        ext = Path(file.filename).suffix.lower()
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{ext}' not allowed. Allowed: {allowed_extensions}",
            )

    # Check size
    contents = await file.read()
    if len(contents) > settings.max_file_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {settings.MAX_FILE_SIZE_MB}MB.",
        )

    dest_dir = settings.upload_path / subfolder
    dest_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename).suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = dest_dir / unique_name

    async with aiofiles.open(dest_path, "wb") as f:
        await f.write(contents)

    return str(dest_path), file.filename


def delete_file(path: str) -> None:
    p = Path(path)
    if p.exists():
        p.unlink()