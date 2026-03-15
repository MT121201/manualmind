from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # This configuration tells Pydantic to read from a .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore" # Ignore extra variables not defined in this class
    )

    PROJECT_NAME: str = "ManualMind API"
    PROJECT_VERSION: str = "1.0.0"

    # MongoDB
    MONGO_URI: str
    MONGO_DB_NAME: str

    # Redis
    REDIS_URL: str
    CACHE_TTL_SECONDS: int = 3600

    # MinIO
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET_NAME: str
    MINIO_SECURE: bool = False

    # Qdrant
    QDRANT_HOST: str
    QDRANT_PORT: int

    # Celery & RabbitMQ
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # LLM & AI Keys
    GOOGLE_API_KEY: str
    OPENAI_API_KEY: str = "your-api-key-here" # Kept for backward compatibility

    # AUTH
    JWT_SECRET: str = "your-jwt-secret-here"

    # 🧠 The smart, slow model for complex LangGraph routing
    REASONING_MODEL: str = "gemini-2.5-flash"

    # ⚡ The fast, cheap model for background tasks like summarization
    FAST_MODEL: str = "gemini-2.5-flash-lite"

    # 📚 The embedding model for Qdrant
    EMBEDDING_MODEL: str = "models/text-embedding-004"

    # LangSmith Observability
    LANGCHAIN_TRACING_V2: str = "false"  # Defaults to false so tests don't fail if key is missing
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGCHAIN_API_KEY: str | None = None
    LANGCHAIN_PROJECT: str = "default-project"

# Instantiate the settings
settings = Settings()