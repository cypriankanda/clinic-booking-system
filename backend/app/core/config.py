from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central app configuration, loaded from environment variables / .env.

    DATABASE_URL defaults to a local SQLite file so the project runs with
    zero external setup. Point it at Postgres in production, e.g.:
        postgresql+psycopg2://user:password@host:5432/clinic
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./clinic.db"
    slot_duration_minutes: int = 30
    min_booking_notice_minutes: int = 60  # bonus requirement: 1-hour buffer
    environment: str = "development"


settings = Settings()
