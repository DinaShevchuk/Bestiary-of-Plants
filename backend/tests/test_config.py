from pathlib import Path

from backend.app.config import PROJECT_ROOT, Settings


def test_loopback_openai_compatible_server_needs_no_fake_api_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:8080/v1")
    monkeypatch.setenv("LLM_MODEL", "bestiary-kunoichi")
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    settings = Settings.from_env()
    assert settings.llm_configured is True


def test_remote_openai_compatible_server_still_requires_api_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.example.org/v1")
    monkeypatch.setenv("LLM_MODEL", "model-name")
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    settings = Settings.from_env()
    assert settings.llm_configured is False


def test_relative_database_path_is_rooted_at_project(monkeypatch):
    monkeypatch.setenv("SQLITE_DB_PATH", "data/bestiary.db")
    assert Settings.from_env().sqlite_db_path == (PROJECT_ROOT / "data" / "bestiary.db").resolve()
