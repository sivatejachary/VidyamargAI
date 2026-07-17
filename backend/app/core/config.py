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
                        key = k.strip()
                        val = v.strip().strip('"').strip("'")
                        if key not in os.environ:
                            os.environ[key] = val
            break
        except Exception:
            pass

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "HireAI API"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "vidyamarg-ai-secret-key-production-fallback-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 15 minutes
    
    # Database (Fallback to production Railway PostgreSQL)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:CDVByqTUKjxAlWjBkyOIjXTAlcAaakUf@hayabusa.proxy.rlwy.net:42919/railway"
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
    NVIDIA_API_KEY_FALLBACK: str = os.getenv("NVIDIA_API_KEY_FALLBACK", "")
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")
    QDRANT_URL: str = os.getenv("QDRANT_URL", "")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "")
    
    # Telegram API
    TG_API_ID: str = os.getenv("TG_API_ID", os.getenv("api_id", ""))
    TG_API_HASH: str = os.getenv("TG_API_HASH", os.getenv("api_hash", ""))
    # Path to the channels list .txt file (overridable for Docker volume mounts)
    TG_CHANNELS_FILE: str = os.getenv(
        "TG_CHANNELS_FILE",
        os.path.join(os.path.dirname(__file__), "../job_agent/channel.txt")
    )
    
    # Feature Flags
    AI_MENTOR_ENABLED: bool = os.getenv("AI_MENTOR_ENABLED", "True").lower() == "true"
    VOICE_MENTOR_ENABLED: bool = os.getenv("VOICE_MENTOR_ENABLED", "False").lower() == "true"
    STUDY_PLAN_ENABLED: bool = os.getenv("STUDY_PLAN_ENABLED", "True").lower() == "true"
    ARTIFACTS_ENABLED: bool = os.getenv("ARTIFACTS_ENABLED", "True").lower() == "true"
    SEARCH_ENABLED: bool = os.getenv("SEARCH_ENABLED", "True").lower() == "true"
    ANALYTICS_ENABLED: bool = os.getenv("ANALYTICS_ENABLED", "False").lower() == "true"
    
    # Auto Apply Agent
    CREDENTIAL_ENCRYPTION_KEY: str = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "")
    AUTO_APPLY_MAX_CONCURRENT: int = int(os.getenv("AUTO_APPLY_MAX_CONCURRENT", "5"))
    AUTO_APPLY_DAILY_CAP: int = int(os.getenv("AUTO_APPLY_DAILY_CAP", "50"))
    AUTO_APPLY_MIN_MATCH_SCORE: float = float(os.getenv("AUTO_APPLY_MIN_MATCH_SCORE", "80.0"))
    AUTO_APPLY_MIN_SKILL_MATCH: float = float(os.getenv("AUTO_APPLY_MIN_SKILL_MATCH", "70.0"))
    AUTO_APPLY_MAX_JOB_AGE_DAYS: int = int(os.getenv("AUTO_APPLY_MAX_JOB_AGE_DAYS", "2"))
    AUTO_APPLY_CHECKPOINT_DB: str = os.getenv("AUTO_APPLY_CHECKPOINT_DB", "storage/langgraph_checkpoints/auto_apply.db")
    PLATFORM_DISABLE_THRESHOLD: float = float(os.getenv("PLATFORM_DISABLE_THRESHOLD", "0.20"))
    PLATFORM_MIN_ATTEMPTS_BEFORE_CHECK: int = int(os.getenv("PLATFORM_MIN_ATTEMPTS_BEFORE_CHECK", "10"))
    
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
        SECRET_KEY = os.getenv("SECRET_KEY", "vidyamarg-ai-secret-key-production-fallback-2026")
        ALGORITHM = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES = 15
        DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:CDVByqTUKjxAlWjBkyOIjXTAlcAaakUf@hayabusa.proxy.rlwy.net:42919/railway"
        )
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
        NVIDIA_API_KEY_FALLBACK = os.getenv("NVIDIA_API_KEY_FALLBACK", "")
        SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
        QDRANT_URL = os.getenv("QDRANT_URL", "")
        QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
        TG_API_ID = os.getenv("TG_API_ID", os.getenv("api_id", ""))
        TG_API_HASH = os.getenv("TG_API_HASH", os.getenv("api_hash", ""))
        TG_CHANNELS_FILE = os.getenv(
            "TG_CHANNELS_FILE",
            os.path.join(os.path.dirname(__file__), "../job_agent/channel.txt")
        )

        AI_MENTOR_ENABLED = os.getenv("AI_MENTOR_ENABLED", "True").lower() == "true"
        VOICE_MENTOR_ENABLED = os.getenv("VOICE_MENTOR_ENABLED", "False").lower() == "true"
        STUDY_PLAN_ENABLED = os.getenv("STUDY_PLAN_ENABLED", "True").lower() == "true"
        ARTIFACTS_ENABLED = os.getenv("ARTIFACTS_ENABLED", "True").lower() == "true"
        SEARCH_ENABLED = os.getenv("SEARCH_ENABLED", "True").lower() == "true"
        ANALYTICS_ENABLED = os.getenv("ANALYTICS_ENABLED", "False").lower() == "true"
        
        # Auto Apply Agent
        CREDENTIAL_ENCRYPTION_KEY = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "")
        AUTO_APPLY_MAX_CONCURRENT = int(os.getenv("AUTO_APPLY_MAX_CONCURRENT", "5"))
        AUTO_APPLY_DAILY_CAP = int(os.getenv("AUTO_APPLY_DAILY_CAP", "50"))
        AUTO_APPLY_MIN_MATCH_SCORE = float(os.getenv("AUTO_APPLY_MIN_MATCH_SCORE", "80.0"))
        AUTO_APPLY_MIN_SKILL_MATCH = float(os.getenv("AUTO_APPLY_MIN_SKILL_MATCH", "70.0"))
        AUTO_APPLY_MAX_JOB_AGE_DAYS = int(os.getenv("AUTO_APPLY_MAX_JOB_AGE_DAYS", "2"))
        AUTO_APPLY_CHECKPOINT_DB = os.getenv("AUTO_APPLY_CHECKPOINT_DB", "storage/langgraph_checkpoints/auto_apply.db")
        PLATFORM_DISABLE_THRESHOLD = float(os.getenv("PLATFORM_DISABLE_THRESHOLD", "0.20"))
        PLATFORM_MIN_ATTEMPTS_BEFORE_CHECK = int(os.getenv("PLATFORM_MIN_ATTEMPTS_BEFORE_CHECK", "10"))
    settings = ManualSettings()

if not settings.SECRET_KEY:
    settings.SECRET_KEY = "vidyamarg-ai-secret-key-production-fallback-2026"

