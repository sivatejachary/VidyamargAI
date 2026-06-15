from pathlib import Path
from app.core.config import settings

# Base directory for local file storage fallback
STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(exist_ok=True)

# Create folders matching storage structure
(STORAGE_DIR / "resumes").mkdir(exist_ok=True)
(STORAGE_DIR / "interview-recordings").mkdir(exist_ok=True)
(STORAGE_DIR / "offer-letters").mkdir(exist_ok=True)
(STORAGE_DIR / "reports").mkdir(exist_ok=True)

class StorageService:
    def __init__(self):
        self.use_minio = False
        # Try importing minio and testing connection if settings are provided
        if settings.MINIO_ENDPOINT and settings.MINIO_ACCESS_KEY != "minioadmin":
            try:
                from minio import Minio
                self.client = Minio(
                    settings.MINIO_ENDPOINT,
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    secure=settings.MINIO_SECURE
                )
                # Ensure bucket exists
                if not self.client.bucket_exists(settings.MINIO_BUCKET):
                    self.client.make_bucket(settings.MINIO_BUCKET)
                self.use_minio = True
            except Exception:
                # Fallback to local storage
                self.use_minio = False

    def upload_file(self, folder: str, filename: str, content: bytes) -> str:
        """
        Uploads a file to MinIO bucket or falls back to local storage directory.
        Returns the accessible URL/path of the file.
        """
        if self.use_minio:
            import io
            bucket_path = f"{folder}/{filename}"
            try:
                self.client.put_object(
                    settings.MINIO_BUCKET,
                    bucket_path,
                    io.BytesIO(content),
                    len(content)
                )
                # In standard MinIO deployment, return URL
                return f"http://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{bucket_path}"
            except Exception:
                # Fallback to local on error
                pass
                
        # Local Storage Fallback
        target_path = STORAGE_DIR / folder / filename
        with open(target_path, "wb") as f:
            f.write(content)
        # Return path that can be retrieved via static route or api
        return f"/api/v1/storage/{folder}/{filename}"

    def get_file_content(self, folder: str, filename: str) -> bytes:
        """
        Retrieves binary content of the file.
        """
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

storage_service = StorageService()
