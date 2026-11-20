"""Runtime configuration. Secrets are read only from environment/.env."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> None:
    """Small .env reader to keep the default install dependency-light."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def _float_env(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def _project_path(name: str, default: Path) -> Path:
    """Resolve relative data paths against the repository, not shell CWD."""
    value = Path(os.getenv(name, str(default))).expanduser()
    return value if value.is_absolute() else (PROJECT_ROOT / value).resolve()


_load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    project_root: Path = PROJECT_ROOT
    data_file: Path = PROJECT_ROOT / "data" / "plants.jsonl"
    data_source: str = "jsonl"
    sqlite_db_path: Path = PROJECT_ROOT / "data" / "bestiary.db"
    llm_provider: str = "none"
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "qwen2.5:7b"
    llm_api_key: str = ""
    llm_timeout_seconds: int = 90
    agentic_enabled: bool = True
    agent_max_tool_calls: int = 5
    agent_max_context_chunks: int = 12
    max_context_chars: int = 24000
    retrieval_top_k: int = 5
    min_bm25_score: float = 0.20
    bm25_k1: float = 1.2
    bm25_b: float = 0.75
    plantnet_api_key: str = ""
    plantnet_api_url: str = "https://my-api.plantnet.org/v2/identify/all"
    max_upload_bytes: int = 10 * 1024 * 1024
    cors_origins: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> "Settings":
        provider = os.getenv("LLM_PROVIDER", "none").strip().lower()
        if provider not in {"none", "ollama", "openai_compatible"}:
            provider = "none"
        origins = tuple(x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip())
        return cls(
            data_file=_project_path("DATA_FILE", PROJECT_ROOT / "data" / "plants.jsonl"),
            data_source=os.getenv("DATA_SOURCE", "jsonl").strip().lower() if os.getenv("DATA_SOURCE", "jsonl").strip().lower() in {"jsonl", "sqlite"} else "jsonl",
            sqlite_db_path=_project_path("SQLITE_DB_PATH", PROJECT_ROOT / "data" / "bestiary.db"),
            llm_provider=provider,
            llm_base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/"),
            llm_model=os.getenv("LLM_MODEL", "qwen2.5:7b"),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            llm_timeout_seconds=_int_env("LLM_TIMEOUT_SECONDS", 90, 5, 300),
            agentic_enabled=os.getenv("AGENTIC_ENABLED", "true").lower() in {"1", "true", "yes", "on"},
            agent_max_tool_calls=_int_env("AGENT_MAX_TOOL_CALLS", 5, 0, 10),
            agent_max_context_chunks=_int_env("AGENT_MAX_CONTEXT_CHUNKS", 12, 1, 30),
            max_context_chars=_int_env("MAX_CONTEXT_CHARS", 24000, 2000, 100000),
            retrieval_top_k=_int_env("RETRIEVAL_TOP_K", 5, 1, 10),
            bm25_k1=_float_env("BM25_K1", 1.2, 0.1, 3.0),
            bm25_b=_float_env("BM25_B", 0.75, 0.0, 1.0),
            plantnet_api_key=os.getenv("PLANTNET_API_KEY", ""),
            plantnet_api_url=os.getenv("PLANTNET_API_URL", "https://my-api.plantnet.org/v2/identify/all"),
            max_upload_bytes=_int_env("MAX_UPLOAD_BYTES", 10 * 1024 * 1024, 1024 * 1024, 25 * 1024 * 1024),
            cors_origins=origins,
        )

    @property
    def llm_configured(self) -> bool:
        if self.llm_provider == "none" or not self.llm_model:
            return False
        if self.llm_provider == "ollama":
            return True
        # Local OpenAI-compatible servers (llama.cpp, KoboldCpp, LM Studio)
        # commonly run without authentication. Do not require a fake key for loopback.
        from urllib.parse import urlparse
        host = (urlparse(self.llm_base_url).hostname or "").lower()
        is_loopback = host in {"localhost", "127.0.0.1", "::1"}
        return bool(self.llm_api_key) or (self.llm_provider == "openai_compatible" and is_loopback)

    @property
    def identification_configured(self) -> bool:
        return bool(self.plantnet_api_key)
