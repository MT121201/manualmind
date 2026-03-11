from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # This automatically looks for a .env file in the same directory
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    MONGO_URI: str
    MONGO_DB_NAME: str
    REDIS_URL: str
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool = False
    MINIO_BUCKET_NAME: str
    QDRANT_HOST: str
    QDRANT_PORT: int
    GOOGLE_API_KEY: str

# Instantiate the settings object
settings = Settings()