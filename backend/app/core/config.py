"""Settings loaded from environment variables (and an optional .env file).

Secrets (e.g. llm_api_key) live only here and are never returned by the API.
"""
from __future__ import annotations

import dataclasses
import os
from dataclasses import dataclass
from pathlib import Path

# backend/app/core/config.py -> parents[3] is the repository root
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:  # python-dotenv is optional at runtime
        return
    load_dotenv(PROJECT_ROOT / ".env", override=False)


def _bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    temp_dir: Path
    database_url: str
    supported_languages: tuple = ("en", "ta")
    story_provider: str = "mock"
    run_jobs_inline: bool = False  # True runs jobs synchronously (used by tests)
    job_workers: int = 2
    max_scenes: int = 200
    cors_origins: tuple = ("http://localhost:5173", "http://127.0.0.1:5173")
    llm_api_key: str | None = None  # secret: never log or return
    network_features_enabled: bool = False

    @property
    def projects_dir(self) -> Path:
        return self.data_dir / "projects"

    @property
    def characters_dir(self) -> Path:
        return self.data_dir / "characters"

    @classmethod
    def from_env(cls) -> "Settings":
        _load_dotenv()
        data_dir = Path(os.environ.get("WONDERTOONS_DATA_DIR") or PROJECT_ROOT / "data").resolve()
        temp_dir = Path(os.environ.get("WONDERTOONS_TEMP_DIR") or data_dir / "tmp").resolve()
        db_url = os.environ.get("WONDERTOONS_DATABASE_URL") or f"sqlite:///{(data_dir / 'wondertoons.db').as_posix()}"
        langs = tuple(
            x.strip().lower()
            for x in os.environ.get("WONDERTOONS_SUPPORTED_LANGUAGES", "en,ta").split(",")
            if x.strip()
        )
        cors_origins = tuple(
            origin.strip()
            for origin in os.environ.get(
                "WONDERTOONS_CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if origin.strip()
        )
        return cls(
            data_dir=data_dir,
            temp_dir=temp_dir,
            database_url=db_url,
            supported_languages=langs or ("en", "ta"),
            story_provider=os.environ.get("WONDERTOONS_STORY_PROVIDER", "mock").strip() or "mock",
            run_jobs_inline=_bool("WONDERTOONS_JOBS_INLINE"),
            job_workers=max(1, int(os.environ.get("WONDERTOONS_JOB_WORKERS", "2"))),
            max_scenes=max(2, int(os.environ.get("WONDERTOONS_MAX_SCENES", "200"))),
            cors_origins=cors_origins,
            llm_api_key=os.environ.get("WONDERTOONS_LLM_API_KEY") or None,
            network_features_enabled=_bool("WONDERTOONS_ALLOW_NETWORK_FEATURES", False),
        )

    @classmethod
    def for_testing(cls, tmp: Path, **overrides) -> "Settings":
        base = cls(
            data_dir=tmp,
            temp_dir=tmp / "tmp",
            database_url=f"sqlite:///{(tmp / 'test.db').as_posix()}",
            run_jobs_inline=True,
            llm_api_key=None,
        )
        return dataclasses.replace(base, **overrides)
