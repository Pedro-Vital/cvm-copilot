"""Application settings — single source of truth for backend env config.

Import `settings` wherever config is needed. Never call `os.getenv` or
`load_dotenv` elsewhere; if a third-party SDK reads `os.environ` directly,
mirror the value here instead.
"""

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Supabase (Auth + API) ---
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # --- Postgres (Alembic + direct DB access) ---
    # Supabase hands out a bare `postgresql://` URL, which SQLAlchemy would
    # default to the psycopg2 driver. This project depends on psycopg (v3),
    # so the driver is normalized here rather than requiring everyone to
    # hand-edit `.env` with a `+psycopg` suffix.
    database_url: str

    @field_validator("database_url", mode="after")
    @classmethod
    def _use_psycopg_driver(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    # --- OpenAI ---
    openai_api_key: str
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536

    # --- Retrieval ---
    # Over-fetch from each search path before fusion so a chunk ranked low by
    # one retriever but high by the other still reaches RRF.
    retrieval_candidate_k: int = 50
    retrieval_top_k: int = 10
    retrieval_rrf_k: int = 60
    retrieval_neighbor_radius: int = 1

    # --- Server ---
    allowed_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_allowed_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()
