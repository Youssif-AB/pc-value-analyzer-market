from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
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
    cors_origins: str = "http://localhost:5173,http://localhost:8082"

    # Live market configuration. Credentials are intentionally environment-only.
    market_currency: str = "CAD"
    live_market_enabled: bool = True
    live_comp_max_age_hours: int = 72
    live_comp_max_results: int = 12
    live_comp_min_similarity: float = 0.52
    live_comp_blend_cap: float = 0.68
    market_cache_ttl_hours: int = 24
    market_refresh_token: str | None = None

    ebay_client_id: str | None = None
    ebay_client_secret: str | None = None
    ebay_marketplace_id: str = "EBAY_CA"
    ebay_category_id: str = "179"
    ebay_search_queries: str = "gaming desktop,rtx gaming pc,custom gaming pc"
    ebay_result_limit: int = 50

    bestbuy_api_key: str | None = None
    bestbuy_category_id: str = "pcmcat287600050002"
    bestbuy_result_limit: int = 100

    serpapi_api_key: str | None = None

    google_shopping_queries: str = (
        "gaming desktop,"
        "RTX gaming PC,"
        "Ryzen gaming desktop,"
        "prebuilt gaming PC,"
        "custom gaming PC"
    )

    google_shopping_location: str = "Calgary, Alberta, Canada"
    google_shopping_gl: str = "ca"
    google_shopping_hl: str = "en"
    google_shopping_currency: str = "CAD"
    google_shopping_result_limit: int = 40

    bank_of_canada_fx_enabled: bool = True
    usd_to_cad_override: float | None = None


    @field_validator("usd_to_cad_override", mode="before")
    @classmethod
    def blank_optional_float(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def ebay_queries(self) -> list[str]:
        return [item.strip() for item in self.ebay_search_queries.split(",") if item.strip()]

    @property
    def configured_market_sources(self) -> list[str]:
        sources: list[str] = []

        if self.ebay_client_id and self.ebay_client_secret:
            sources.append("ebay")

        if self.serpapi_api_key:
            sources.append("google_shopping")

        if self.bestbuy_api_key:
            sources.append("bestbuy")

        return sources

    @property
    def google_shopping_query_list(self) -> list[str]:
        return [
            item.strip()
            for item in self.google_shopping_queries.split(",")
            if item.strip()
        ]

@lru_cache
def get_settings() -> Settings:
    return Settings()
