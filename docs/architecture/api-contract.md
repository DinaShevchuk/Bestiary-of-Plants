# API-контракт (реализован)

**Base URL локально:** `http://127.0.0.1:8000`  
**Префикс API:** `/api/v1`  
**Формат:** JSON UTF-8, кроме multipart upload для изображения.

## 1. Общие соглашения

- API key LLM и PlantNet хранится только в `.env` backend.
- `document_id` стабилен в пределах корпуса; `chunk_id` имеет вид `<document_id>#chunk-NNN`.
- `source_ref` (`S1`, `S2`, …) назначается backend для цитирования внутри текущего ответа.
- `source_url` может быть `null`; frontend не создаёт ссылки самостоятельно.
- `score` BM25 — ранжирующая величина, не вероятность.

## 2. Health — `GET /api/v1/health`

Возвращает состояние сервиса и размеры корпуса.

```json
{
  "status": "ok",
  "service": "bestiary-of-plants",
  "corpus": {
    "documents": 4,
    "chunks": 4,
    "indexed_chunks": 4,
    "indexed_terms": 189,
    "average_chunk_length": 63.5,
    "k1": 1.2,
    "b": 0.75
  }
}
```

Числа выше — пример для текущего seed-корпуса; после изменения данных они изменятся.

## 3. Public config — `GET /api/v1/config`

Показывает frontend только публичные флаги: `llm_configured`, `llm_provider`, модель (только если LLM включена), `agentic_enabled`, лимиты инструментов/контекста, `identification_configured`, retrieval method и статистику корпуса. Секреты и API keys не возвращаются.

## 4. BM25 Search — `GET /api/v1/search`

| Query | Тип | Обязателен | Диапазон |
|---|---|---|---|
| `q` | string | да | 1–1000 символов, не пустой после trim |
| `limit` | integer | нет | 1–10, default 5 |

```http
GET /api/v1/search?q=венерина%20мухоловка&limit=5
```

Успешный ответ: `{ "query": "...", "method": "bm25", "results": [...] }`. У результата есть `document_id`, `chunk_id`, `title`, `scientific_name`, `snippet`, `source_title`, `source_url`, `record_status`, `score`.

## 5. Ask / RAG — `POST /api/v1/ask`

Тело запроса:

```json
{
  "query": "Венерина мухоловка ловушка створки",
  "limit": 5,
  "agentic": true
}
```

`query`: 1–1000 символов; `limit`: 1–10; `agentic`: необязательный bool, если отсутствует — используется `AGENTIC_ENABLED`.

Успешный ответ:

```json
{
  "query": "...",
  "answer": "... [S1]",
  "status": "answered",
  "generation_mode": "rag",
  "sources": [
    {
      "source_ref": "S1",
      "chunk_id": "plant-example#chunk-001",
      "document_id": "plant-example",
      "title": "Название растения",
      "scientific_name": null,
      "source_title": "Название источника",
      "source_url": null,
      "snippet": "...",
      "score": 1.23,
      "record_status": "reviewed"
    }
  ],
  "retrieval": {
    "method": "bm25",
    "initial_results": 1,
    "total_context_chunks": 1,
    "tool_calls": 0,
    "max_tool_calls": 5
  }
}
```

`generation_mode`: `rag`, `agentic_rag`, `retrieval_only` или `none`. `status`: `answered` или `insufficient_data`. При отсутствии LLM система показывает найденные выдержки с `generation_mode=retrieval_only` — это не генеративный ответ. При отсутствии контекста возвращается честное сообщение, пустые `sources` и `status=insufficient_data`.

## 6. Plant profile — `GET /api/v1/plants/{document_id}`

Возвращает исходную запись по стабильному ID. `404` с кодом `PLANT_NOT_FOUND`, если записи нет.

## 7. Image identification — `POST /api/v1/identify`

`multipart/form-data`, поле `image` обязательно; query-параметр `organ` допускает `auto|leaf|flower|fruit|bark|habit`.

Поддерживаются JPEG и PNG, до 10 МБ по умолчанию. Ответ содержит `status=identified|no_match`, сообщение о предварительном характере результата, `candidates[]` (`scientific_name`, `common_names`, `score`) и `provider=Pl@ntNet`. Score — показатель внешнего сервиса, не гарантия правильности. Endpoint возвращает `503 IDENTIFICATION_NOT_CONFIGURED`, если отсутствует `PLANTNET_API_KEY`.

## 8. Ошибки

FastAPI возвращает стандартный формат `detail`; для прикладных ошибок в `detail` содержатся `code` и `message`. Основные статусы:

- `400` — некорректный файл/пустое изображение;
- `413` — превышен размер файла;
- `415` — неподдерживаемый MIME type или сигнатура содержимого не соответствует JPEG/PNG;
- `422` — ошибка валидации query/body;
- `404` — карточка не найдена;
- `502` — внешний сервис распознавания недоступен/вернул ошибку;
- `503` — фотоидентификация не настроена.

Stack trace, секреты и тело ошибки провайдера пользователю не передаются.

## 9. LLM provider settings

Выбор провайдера выполняется backend конфигурацией, а не произвольным URL из браузера:

- `LLM_PROVIDER=none` — BM25 и выдержки без LLM;
- `LLM_PROVIDER=ollama` — OpenAI-compatible endpoint Ollama, обычно `http://localhost:11434/v1`;
- `LLM_PROVIDER=openai_compatible` — любой endpoint с `/v1/chat/completions`; для удалённых endpoint нужен API key, для loopback `localhost`/`127.0.0.1`/`::1` ключ можно оставить пустым (llama.cpp, KoboldCpp).

Вызовы tools делаются только из allowlist backend. Максимум 10 вызовов на запрос.


## 10. Deployment boundary

Текущая версия рассчитана на локальный или контролируемый запуск. API не содержит полноценной пользовательской аутентификации, rate limiting и server-side authorization. Не публикуйте backend в открытый интернет без отдельного hardening-этапа.
