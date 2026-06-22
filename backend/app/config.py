from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "sqlite:///./pcvalue.sqlite3"
    mlflow_tracking_uri: str = "http://localhost:5000"
    mlflow_experiment_name: str = "pc-value-analyzer"
    model_name: str = "pc-value-regressor"
    model_alias: str = "champion"
    model_artifact_path: Path = Path("backend/artifacts/price_model.joblib")
    model_metadata_path: Path = Path("backend/artifacts/model_metadata.json")
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
