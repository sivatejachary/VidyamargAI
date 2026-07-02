"""
storage.py — Unified storage service (MinIO / local fallback).

Phase 6 enhancements:
  - Presigned URLs for MinIO objects (1-hour expiry by default)
  - CDN URL rewriting (set STORAGE_CDN_BASE to activate)
  - MIME-type allow-list guard
  - File-size hard limit (50 MB)
  - Graceful local fallback
"""
from __future__ import annotations

import io
import logging
import os
from datetime import timedelta
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("app.storage")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STORAGE_DIR = Path("storage")


def _ensure_storage_dirs() -> None:
    """Create local storage directories on first use (lazy, Railway-safe)."""
    try:
        STORAGE_DIR.mkdir(exist_ok=True)
        for _sub in ("resumes", "interview-recordings", "offer-letters", "reports", "thumbnails"):
            (STORAGE_DIR / _sub).mkdir(exist_ok=True)
    except OSError as exc:
        logger.warning("Could not create storage directories: %s", exc)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB hard limit

ALLOWED_MIME_TYPES = {
    # Documents
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    # Images
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    # Videos
    "video/mp4",
    "video/webm",
    # Audio
    "audio/mpeg",
    "audio/wav",
    "audio/webm",
    # Plain text / JSON (for reports)
    "text/plain",
    "application/json",
}

# Optional CDN base URL.  E.g. "https://cdn.example.com"
# When set, MinIO object URLs are rewritten to CDN URLs.
STORAGE_CDN_BASE: Optional[str] = os.getenv("STORAGE_CDN_BASE", "").strip() or None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_user_folder_name(user) -> str:
    full_name = getattr(user, "full_name", None)
    email = getattr(user, "email", None)
    user_id = getattr(user, "id", None)

    name = full_name or (email.split("@")[0] if email else None)
    if not name:
        name = f"user_{user_id or 'unknown'}"

    sanitized = "".join(c if c.isalnum() or c in (" ", "_", "-") else "" for c in name).strip()
    sanitized = sanitized.replace(" ", "_")
    if not sanitized:
        sanitized = f"user_{user_id or 'unknown'}"
    return f"{sanitized}_{user_id or 'unknown'}"


def _rewrite_to_cdn(minio_url: str) -> str:
    """Rewrite a MinIO object URL to the CDN base URL."""
    if not STORAGE_CDN_BASE:
        return minio_url
    # Replace the scheme+host+bucket with CDN base
    # MinIO URL pattern: http://<endpoint>/<bucket>/<path>
    try:
        from urllib.parse import urlparse
        parsed = urlparse(minio_url)
        # path starts with "/<bucket>/<object_path>"
        # strip the leading /<bucket>
        path_parts = parsed.path.lstrip("/").split("/", 1)
        object_path = path_parts[1] if len(path_parts) > 1 else path_parts[0]
        return f"{STORAGE_CDN_BASE.rstrip('/')}/{object_path}"
    except Exception:
        return minio_url


# ---------------------------------------------------------------------------
# StorageService
# ---------------------------------------------------------------------------
class StorageService:
    def __init__(self):
        self.use_minio = False
        if settings.MINIO_ENDPOINT and settings.MINIO_ACCESS_KEY != "minioadmin":
            try:
                from minio import Minio

                region = settings.MINIO_REGION
                if not region or region.lower() == "undefined":
                    region = "us-east-1"

                self.client = Minio(
                    settings.MINIO_ENDPOINT,
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    secure=settings.MINIO_SECURE,
                    region=region,
                )
                if not self.client.bucket_exists(settings.MINIO_BUCKET):
                    self.client.make_bucket(settings.MINIO_BUCKET)
                self.use_minio = True
                logger.info("StorageService: using MinIO backend")
            except Exception as exc:
                logger.warning("StorageService: MinIO unavailable (%s); using local storage", exc)
                self.use_minio = False
        else:
            logger.info("StorageService: using local storage backend")

    # -----------------------------------------------------------------------
    def validate_upload(self, content: bytes, mime_type: Optional[str] = None) -> None:
        """Raise ValueError for oversized or disallowed file types."""
        if len(content) > MAX_FILE_SIZE:
            raise ValueError(f"File size {len(content)} exceeds limit of {MAX_FILE_SIZE} bytes")
        if mime_type and mime_type not in ALLOWED_MIME_TYPES:
            raise ValueError(f"MIME type '{mime_type}' is not allowed")

    # -----------------------------------------------------------------------
    def upload_file(
        self,
        folder: str,
        filename: str,
        content: bytes,
        mime_type: Optional[str] = None,
    ) -> str:
        """
        Upload a file to MinIO or local storage.
        Returns a presigned URL (MinIO) or a local API path.
        Raises ValueError for oversized / disallowed MIME types.
        """
        self.validate_upload(content, mime_type)

        if self.use_minio:
            bucket_path = f"{folder}/{filename}"
            content_type = mime_type or "application/octet-stream"
            try:
                self.client.put_object(
                    settings.MINIO_BUCKET,
                    bucket_path,
                    io.BytesIO(content),
                    len(content),
                    content_type=content_type,
                )
                # Return presigned URL (1 hour)
                url = self.client.presigned_get_object(
                    settings.MINIO_BUCKET,
                    bucket_path,
                    expires=timedelta(hours=1),
                )
                return _rewrite_to_cdn(url) if STORAGE_CDN_BASE else url
            except Exception as exc:
                logger.warning("MinIO upload failed (%s); falling back to local", exc)

        # Local Storage Fallback
        _ensure_storage_dirs()
        target_dir = STORAGE_DIR / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename
        with open(target_path, "wb") as f:
            f.write(content)
        return f"/api/v1/storage/{folder}/{filename}"

    # -----------------------------------------------------------------------
    def get_presigned_url(
        self,
        folder: str,
        filename: str,
        expires_hours: int = 1,
    ) -> str:
        """
        Generate a fresh presigned URL for an existing MinIO object.
        Falls back to the local API path if MinIO is unavailable.
        """
        if self.use_minio:
            try:
                bucket_path = f"{folder}/{filename}"
                url = self.client.presigned_get_object(
                    settings.MINIO_BUCKET,
                    bucket_path,
                    expires=timedelta(hours=expires_hours),
                )
                return _rewrite_to_cdn(url) if STORAGE_CDN_BASE else url
            except Exception as exc:
                logger.warning("presigned_get_object failed: %s", exc)
        return f"/api/v1/storage/{folder}/{filename}"

    # -----------------------------------------------------------------------
    def get_file_content(self, folder: str, filename: str) -> bytes:
        """Retrieve binary content of the file."""
        if self.use_minio:
            try:
                bucket_path = f"{folder}/{filename}"
                response = self.client.get_object(settings.MINIO_BUCKET, bucket_path)
                return response.read()
            except Exception:
                pass

        target_path = STORAGE_DIR / folder / filename
        if not target_path.exists():
            return b""
        with open(target_path, "rb") as f:
            return f.read()

    # -----------------------------------------------------------------------
    def delete_file(self, folder: str, filename: str) -> None:
        """Delete a file from MinIO or local storage."""
        if self.use_minio:
            try:
                bucket_path = f"{folder}/{filename}"
                self.client.remove_object(settings.MINIO_BUCKET, bucket_path)
                return
            except Exception as exc:
                logger.warning("MinIO delete failed: %s", exc)
        try:
            target_path = STORAGE_DIR / folder / filename
            if target_path.exists():
                target_path.unlink()
        except Exception as exc:
            logger.warning("Local delete failed: %s", exc)


storage_service = StorageService()
