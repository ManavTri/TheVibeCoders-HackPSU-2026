from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:5173"
    max_upload_mb: int = 10
    require_auth: bool = False
    auth0_domain: str | None = None
    auth0_audience: str | None = None
    supabase_url: str | None = None
    supabase_service_key: str | None = None
    supabase_jwt_secret: str | None = None
    supabase_jwt_audience: str = "authenticated"
    supabase_storage_bucket: str = "student-documents"
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_timeout_seconds: int = 45

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key and self.llm_api_key.strip())

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
