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
    allowed_origins: str = "http://localhost:8080,http://localhost:5173,http://127.0.0.1:8080"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
