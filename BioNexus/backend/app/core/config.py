import ssl
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote_plus
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """BioNexus Application Settings."""

    APP_NAME: str = "BioNexus API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # CORS (supports comma-separated string or list)
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Database connection parameters
    DATABASE_URL: Optional[str] = None
    DB_HOST: Optional[str] = None
    DB_PORT: int = 4000
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_NAME: str = "bionexus"

    # SSL/TLS Configuration for TiDB Cloud
    DB_SSL_CA: Optional[str] = None
    DB_SSL_VERIFY_CERT: bool = True

    # Database Pool Settings
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # LLM Integrations
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Storage & Data Paths
    DATA_DIR: str = "../../data"

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH) if ENV_PATH.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Union[List[str], str]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(i).strip() for i in parsed if str(i).strip()]
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    def get_database_url(self) -> Optional[str]:
        """Resolve database connection URL from DATABASE_URL or individual fields."""
        if self.DATABASE_URL and self.DATABASE_URL.strip():
            return self.DATABASE_URL.strip()

        if self.DB_HOST and self.DB_USER:
            user = quote_plus(self.DB_USER)
            password = quote_plus(self.DB_PASSWORD or "")
            return f"mysql+pymysql://{user}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

        return None

    def get_ssl_connect_args(self) -> Dict[str, Any]:
        """Return SSL connect arguments for PyMySQL / TiDB Cloud."""
        db_url = self.get_database_url() or ""
        # If using SQLite (e.g. testing), no SSL args needed
        if db_url.startswith("sqlite"):
            return {}

        connect_args: Dict[str, Any] = {}
        ssl_dict: Dict[str, Any] = {}

        if self.DB_SSL_CA:
            ssl_dict["ca"] = self.DB_SSL_CA

        if self.DB_SSL_VERIFY_CERT:
            # Default SSL context for secure TLS connection to TiDB Cloud
            ssl_dict["check_hostname"] = True

        if ssl_dict:
            connect_args["ssl"] = ssl_dict
        elif "tidbcloud.com" in db_url or (self.DB_HOST and "tidbcloud.com" in self.DB_HOST):
            # Default SSL mode required for TiDB Cloud
            connect_args["ssl"] = {"ssl_mode": "VERIFY_IDENTITY"}

        return connect_args

    def get_masked_db_url(self) -> str:
        """Return database URL with password masked for safe logging/inspection."""
        url = self.get_database_url()
        if not url:
            return "Not configured"
        if url.startswith("sqlite"):
            return url
        try:
            from urllib.parse import urlparse, urlunparse

            parsed = urlparse(url)
            if parsed.password:
                netloc = f"{parsed.username}:******@{parsed.hostname}:{parsed.port}"
                return urlunparse(parsed._replace(netloc=netloc))
        except Exception:
            pass
        return "mysql+pymysql://***:***@***"


settings = Settings()
