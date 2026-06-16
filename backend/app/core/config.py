import os

# Load .env file manually if it exists in the workspace root or parent folders
config_dir = os.path.dirname(os.path.abspath(__file__))
for path in [
    os.path.join(config_dir, "../../../.env"),
    os.path.join(config_dir, "../../.env"),
    os.path.join(config_dir, "../.env"),
    ".env"
]:
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")
            break
        except Exception:
            pass

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "HireAI API"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-recruit-tara-key-987654321")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database (Fallback to PostgreSQL local)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:postgres@localhost:5432/hireai"
    )
    
    # Storage (MinIO / S3)
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "False").lower() == "true"
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "hireai")
    MINIO_REGION: str = os.getenv("MINIO_REGION", "us-east-1")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # AI Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    
    # Telegram API
    TG_API_ID: str = os.getenv("TG_API_ID", os.getenv("api_id", ""))
    TG_API_HASH: str = os.getenv("TG_API_HASH", os.getenv("api_hash", ""))
    
    class Config:
        case_sensitive = True

# We use standard Pydantic Settings but fallback gracefully if pydantic-settings isn't installed
try:
    settings = Settings()
except Exception:
    # Manual fallback representation
    class ManualSettings:
        PROJECT_NAME = "HireAI API"
        API_V1_STR = "/api/v1"
        SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-recruit-tara-key-987654321")
        ALGORITHM = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
        DATABASE_URL = os.getenv("DATABASE_URL", _default_db_url)
        MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() == "true"
        MINIO_BUCKET = os.getenv("MINIO_BUCKET", "hireai")
        MINIO_REGION = os.getenv("MINIO_REGION", "us-east-1")
        REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
        TG_API_ID = os.getenv("TG_API_ID", os.getenv("api_id", ""))
        TG_API_HASH = os.getenv("TG_API_HASH", os.getenv("api_hash", ""))
    settings = ManualSettings()
