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

# Instantiate the settings
settings = Settings()