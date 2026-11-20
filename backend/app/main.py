"""FastAPI entry point. Serves the existing frontend and the /api/v1 API."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import requests
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import PROJECT_ROOT, Settings
from .service import PlantKnowledgeService

settings = Settings.from_env()
service = PlantKnowledgeService(settings)

app = FastAPI(
    title="Бестиарий растений API",
    description="BM25 retrieval, RAG, bounded tool-calling and optional PlantNet identification.",
    version="1.0.0",
)
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

for mount_name in ("css", "js", "img"):
    mount_path = PROJECT_ROOT / mount_name
    if mount_path.exists():
        app.mount(f"/{mount_name}", StaticFiles(directory=mount_path), name=mount_name)


class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=5, ge=1, le=10)
    agentic: bool | None = None


@app.get("/api/v1/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "bestiary-of-plants", "corpus": service.stats()}


@app.get("/api/v1/config")
def public_config() -> dict[str, Any]:
    """Expose safe feature flags only; never return keys or private URLs."""
    return {
        "llm_configured": settings.llm_configured,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model if settings.llm_configured else None,
        "agentic_enabled": settings.agentic_enabled,
        "agent_max_tool_calls": settings.agent_max_tool_calls,
        "agent_max_context_chunks": settings.agent_max_context_chunks,
        "identification_configured": settings.identification_configured,
        "retrieval_method": "bm25",
        "data_source": settings.data_source,
        "corpus": service.stats(),
    }


@app.get("/api/v1/search")
def search(q: str = Query(min_length=1, max_length=1000), limit: int = Query(default=5, ge=1, le=10)) -> dict[str, Any]:
    query = q.strip()
    if not query:
        raise HTTPException(status_code=422, detail={"code": "INVALID_QUERY", "message": "Поисковый запрос не должен быть пустым."})
    results = service.search(query, limit)
    return {"query": query, "method": "bm25", "results": [
        {
            "document_id": item.get("document_id"),
            "chunk_id": item.get("chunk_id"),
            "title": item.get("plant_name"),
            "scientific_name": item.get("scientific_name"),
            "snippet": item.get("content"),
            "source_title": item.get("source_title"),
            "source_url": item.get("source_url"),
            "record_status": item.get("record_status"),
            "score": item.get("score"),
        } for item in results
    ]}


@app.post("/api/v1/ask")
def ask(request: AskRequest) -> dict[str, Any]:
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail={"code": "INVALID_QUERY", "message": "Введите название растения или вопрос."})
    return service.ask(query, limit=request.limit, agentic=request.agentic)


@app.get("/api/v1/plants/{document_id}")
def get_plant(document_id: str) -> dict[str, Any]:
    document = service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail={"code": "PLANT_NOT_FOUND", "message": "Растение не найдено в корпусе."})
    record = document.as_dict()
    record.pop("content", None)
    record["content"] = document.content
    return record


@app.post("/api/v1/identify")
async def identify_plant(
    image: UploadFile = File(...),
    organ: str = Query(default="auto", pattern="^(auto|leaf|flower|fruit|bark|habit)$"),
) -> dict[str, Any]:
    """Optional image recognition via PlantNet; it never asserts certainty."""
    if not settings.identification_configured:
        raise HTTPException(status_code=503, detail={"code": "IDENTIFICATION_NOT_CONFIGURED", "message": "Распознавание фото не настроено: добавьте PLANTNET_API_KEY в .env."})
    allowed = {"image/jpeg", "image/png"}
    if image.content_type not in allowed:
        raise HTTPException(status_code=415, detail={"code": "UNSUPPORTED_IMAGE", "message": "Поддерживаются изображения JPEG и PNG."})
    payload = await image.read(settings.max_upload_bytes + 1)
    if not payload:
        raise HTTPException(status_code=400, detail={"code": "EMPTY_IMAGE", "message": "Файл изображения пуст."})
    if len(payload) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail={"code": "IMAGE_TOO_LARGE", "message": "Размер изображения превышает допустимый лимит."})
    valid_signature = (payload.startswith(b"\xff\xd8\xff") if image.content_type == "image/jpeg"
                       else payload.startswith(b"\x89PNG\r\n\x1a\n"))
    if not valid_signature:
        raise HTTPException(status_code=415, detail={"code": "INVALID_IMAGE_CONTENT", "message": "Содержимое файла не соответствует формату JPEG или PNG."})
    filename = Path(image.filename or "plant-image").name
    try:
        response = requests.post(
            settings.plantnet_api_url,
            params={"api-key": settings.plantnet_api_key, "include-related-images": "false"},
            files={"images": (filename, payload, image.content_type)},
            data={"organs": organ},
            timeout=45,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail={"code": "IDENTIFICATION_PROVIDER_UNAVAILABLE", "message": "Сервис распознавания временно недоступен."}) from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail={"code": "IDENTIFICATION_PROVIDER_ERROR", "message": f"Сервис распознавания вернул ошибку HTTP {response.status_code}."})
    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail={"code": "INVALID_IDENTIFICATION_RESPONSE", "message": "Сервис распознавания вернул некорректный ответ."}) from exc
    candidates = []
    for item in data.get("results", [])[:5]:
        species = item.get("species") or {}
        scientific_name = species.get("scientificNameWithoutAuthor") or species.get("scientificName")
        common_names = species.get("commonNames") or []
        candidates.append({
            "scientific_name": scientific_name,
            "common_names": common_names[:5],
            "score": item.get("score"),
        })
    return {
        "status": "identified" if candidates else "no_match",
        "message": "Это вероятные варианты, а не подтверждённое определение. Сверьте несколько признаков растения.",
        "candidates": candidates,
        "provider": "Pl@ntNet",
    }


@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "index.html")


@app.get("/{page_name}.html", include_in_schema=False)
def static_page(page_name: str) -> FileResponse:
    if page_name not in {"login", "register"}:
        raise HTTPException(status_code=404)
    return FileResponse(PROJECT_ROOT / f"{page_name}.html")
