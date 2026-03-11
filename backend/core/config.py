# backend/core/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "ManualMind API"

    # MongoDB
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "manualmind"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "admin"
    MINIO_SECRET_KEY: str = "password123"
    MINIO_BUCKET_NAME: str = "manuals"
    MINIO_SECURE: bool = False  # False because we are running locally without HTTPS

    # Qdrant
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    # Celery & RabbitMQ
    CELERY_BROKER_URL: str = "amqp://guest:guest@localhost:5672//"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # LLM (You can fill this in later)
    OPENAI_API_KEY: str = "your-api-key-here"

    class Config:
        env_file = ".env"


# Instantiate the settings so we can import it anywhere
settings = Settings()