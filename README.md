# Бестиарий растений

**Тип проекта:** веб-справочник с BM25-поиском, RAG-ответами и дополнительным поиском по запросу LLM.  
**Статус:** первый работающий backend и связанный с ним интерфейс реализованы; базовый корпус демонстрационный и требует фактчекинга.  
**Версия реализации:** 1.1.0

## 1. Что уже работает

- [x] Существующий HTML/CSS/JS-интерфейс сохранён и подключён к backend.
- [x] Python + FastAPI backend, API-контракты и раздача frontend с того же сервера.
- [x] BM25 реализован самостоятельно: обратный индекс, TF, IDF, поправка на длину документа и ранжирование.
- [x] Корпус JSONL и SQLite: загрузка таксономии из `plants`, описаний из `plant_descriptions`, документов/источников из `documents`/`sources`; chunking с перекрытием.
- [x] Импорт листа `plants` из `bestiary_datasets.xlsx` в существующую таблицу `plants` с dry-run, проверкой дублей и сохранением уже заполненных полей БД.
- [x] `POST /api/v1/ask`: retrieval → контекст → LLM, возврат ответа и источников; без LLM используется честный режим показа найденных фрагментов.
- [x] Agentic RAG: ограниченные function/tool calls для повторного поиска и получения карточки растения.
- [x] Единый OpenAI-compatible LLM-клиент для Ollama, облачных API и локальных GGUF-серверов llama.cpp/KoboldCpp. Локальные loopback endpoints не требуют фиктивного API key.
- [x] UI показывает ожидание, ошибки, источники и сохраняет историю чатов в `localStorage`.
- [x] Опциональная фотоидентификация через Pl@ntNet API — без обучения собственной модели; пользователь выбирает один из вариантов, после чего выполняется поиск в локальном корпусе.
- [x] Автотесты BM25, загрузки корпуса, RAG-сценариев, ограниченного вызова инструмента и HTTP API.
- [x] Smoke benchmark с результатами в `docs/retrieval/benchmark-results-smoke.json`.

## 2. Схема работы

```mermaid
flowchart TD
    U[Пользователь] --> UI[HTML / JS chat]
    UI --> API[FastAPI /api/v1/ask]
    API --> BM[BM25 index]
    BM --> CTX[Chunks + source metadata]
    CTX --> LLM[Ollama или OpenAI-compatible API]
    LLM -->|tool call, максимум 5 по умолчанию / 10 предел| TOOLS[search_plant_knowledge / get_plant_profile]
    TOOLS --> BM
    LLM --> ANS[Answer + sources]
    ANS --> UI
    PHOTO[Фото] --> IDENT[Pl@ntNet API — опционально]
    IDENT --> CAND[Кандидаты вида]
    CAND -->|подтверждение пользователем| UI
```

BM25 score — величина для ранжирования, **не вероятность** правильности. LLM должна отвечать только по найденному контексту, цитировать `source_ref` и воздерживаться от ответа, если данных недостаточно.

## 3. Требования

- Python 3.10+ (проверялась среда Python 3.13).
- Интернет не нужен для локального BM25 и локального SQLite-корпуса.
- Для локальной генерации можно использовать Ollama или GGUF через llama.cpp/KoboldCpp.
- Для API-генерации нужен ключ и совместимый с OpenAI Chat Completions endpoint.
- Для фото: ключ Pl@ntNet API. Без ключа endpoint распознавания отключён.
- Для импорта Excel: `openpyxl` (устанавливается из `requirements.txt`).

## 4. Установка и запуск

Из корня репозитория:

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Откройте `http://127.0.0.1:8000/`. Документация OpenAPI доступна по `http://127.0.0.1:8000/docs`, health-check — `/api/v1/health`.

Запуск только статического HTML через `python -m http.server` больше не является полным режимом: в нём не работает API, поиск, LLM и фотоидентификация. Для интегрированного приложения запускайте FastAPI-сервер.

## 5. Выбор LLM

### Вариант A — локальная модель через Ollama

1. Установите и запустите Ollama.
2. Загрузите модель, которая поддерживает tools/function calling (например, `qwen2.5:7b`, если этот тег доступен в вашей установке):

```bash
ollama pull qwen2.5:7b
```

3. В `.env` задайте:

```dotenv
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:7b
LLM_API_KEY=
AGENTIC_ENABLED=true
AGENT_MAX_TOOL_CALLS=5
```

Ollama предоставляет OpenAI-совместимый endpoint `/v1/chat/completions`; поддержка tool calling зависит от выбранной модели и её версии. Если модель не умеет возвращать вызовы функций, отключите `AGENTIC_ENABLED` или выберите совместимую модель.

### Вариант B — облачный / OpenAI-compatible API

В `.env`:

```dotenv
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=<доступное-имя-модели>
LLM_API_KEY=<ваш-ключ>
AGENTIC_ENABLED=true
AGENT_MAX_TOOL_CALLS=5
```

Для другого провайдера укажите его базовый URL и модель, совместимые с `POST /v1/chat/completions` и tool calling. Ключ хранится только на backend. Не вставляйте ключ в `index.html`, `js/app.js`, README или Git.

### Вариант C — существующие GGUF из Faraday (llama.cpp server)

Файлы из `C:\Users\user\AppData\Roaming\faraday\models` можно использовать напрямую: копировать их в папку проекта не требуется. Сам путь к `.gguf` не указывается в `.env` приложения. Сначала отдельный inference-сервер загружает файл и предоставляет OpenAI-compatible endpoint.

На Windows установите llama.cpp (если ещё не установлен):

```powershell
winget install -e --id ggml.llamacpp
```

После установки откройте новое окно PowerShell. Для удобства в репозитории есть скрипт, который сам находит GGUF в Faraday-папке и запускает сервер:

```powershell
.\scripts\run-gguf-server.ps1 -Model kunoichi
# или
.\scripts\run-gguf-server.ps1 -Model tiefighter
```

Запустите одну модель за раз. Уточните точное имя файла командой `Get-ChildItem "$env:APPDATA\faraday\models"`; Windows может скрывать расширение `.gguf`.

Пример для Kunoichi:

```powershell
llama-server.exe -m "$env:APPDATA\faraday\models\mistral.7b.kunoichi.gguf_v2.q4_k_m" --alias bestiary-kunoichi --host 127.0.0.1 --port 8080 --ctx-size 4096 --n-gpu-layers 0
```

Пример для Tiefighter (запускайте вместо предыдущей команды, если хотите использовать её):

```powershell
llama-server.exe -m "$env:APPDATA\faraday\models\llama2.13b.tiefighter.gguf_v2.q4_k_m.gguf" --alias bestiary-tiefighter --host 127.0.0.1 --port 8080 --ctx-size 4096 --n-gpu-layers 0
```

Если реальное имя файла отличается, подставьте его целиком. `--n-gpu-layers 0` запускает модель на CPU; при наличии совместимого GPU параметр можно увеличить, исходя из объёма VRAM. Контекст 4096 выбран консервативно для этих поколений моделей.

В `.env` проекта для Kunoichi:

```dotenv
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://127.0.0.1:8080/v1
LLM_MODEL=bestiary-kunoichi
LLM_API_KEY=
AGENTIC_ENABLED=false
AGENT_MAX_TOOL_CALLS=0
MAX_CONTEXT_CHARS=6000
```

Для Tiefighter замените `LLM_MODEL=bestiary-tiefighter`. Из-за отсутствия надёжно подтверждённого function calling для этих старых roleplay-моделей на первом этапе оставьте Agentic RAG выключенным. Базовый RAG работает так: backend делает BM25 → передаёт найденные фрагменты → модель формирует ответ.

Проверить API можно так:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/v1/models
```

Альтернатива — KoboldCpp. Он принимает GGUF напрямую и предоставляет OpenAI-compatible endpoint `http://127.0.0.1:5001/v1`:

```powershell
koboldcpp.exe --model "$env:APPDATA\faraday\models\mistral.7b.kunoichi.gguf_v2.q4_k_m" --host 127.0.0.1 --port 5001 --contextsize 4096
```

Тогда в `.env`: `LLM_BASE_URL=http://127.0.0.1:5001/v1`, `LLM_MODEL=local-model`, `LLM_PROVIDER=openai_compatible`. При необходимости API key можно оставить пустым для loopback адреса.

> Важно: наличие GGUF-контейнера не означает поддержку tools. Kunoichi/Tiefighter подходят для теста обычного RAG, но tool-calling нужно проверять отдельно. Для Agentic RAG разумнее выбрать более современную instruct-модель, у которой явно подтверждена поддержка tool calling.

### Вариант D — поиск без LLM

Оставьте `LLM_PROVIDER=none`. BM25 и API поиска работают без внешней модели. `/ask` вернёт найденные фрагменты в режиме `retrieval_only`, не выдавая их за сгенерированный ответ.

После изменения `.env` перезапустите сервер.

## 6. Agentic RAG и ограничения

LLM получает первичный контекст и два инструмента:

- `search_plant_knowledge(query, limit)` — дополнительный BM25-поиск;
- `get_plant_profile(plant_name)` — расширенное содержимое карточки из локального корпуса.

Настройки:

| Переменная | Значение по умолчанию | Ограничение |
|---|---:|---|
| `AGENTIC_ENABLED` | `true` | `true` / `false` |
| `AGENT_MAX_TOOL_CALLS` | `5` | принудительно ограничивается диапазоном 0–10 |
| `AGENT_MAX_CONTEXT_CHUNKS` | `12` | 1–30 уникальных фрагментов |
| `MAX_CONTEXT_CHARS` | `24000` | 2 000–100 000 символов |
| `RETRIEVAL_TOP_K` | `5` | 1–10 |

Каждый вызов инструмента считается отдельно; повторно найденный chunk не добавляется в контекст второй раз. При достижении лимита следующий запрос к модели отправляется уже без инструментов, чтобы она сформировала ответ по имеющимся данным или отказалась. Если модель всё равно возвращает tool call без разрешённых инструментов, цикл останавливается и backend возвращает безопасную выдержку без генеративного ответа.

## 7. Корпус и BM25

### 7.1. Подключение вашей SQLite-базы

Основной источник проекта теперь можно переключить с демонстрационного JSONL на существующую реляционную БД. В `.env`:

```dotenv
DATA_SOURCE=sqlite
SQLITE_DB_PATH=C:/Users/user/path/to/bestiary.db
```

Положите ваш фактический `bestiary.db` в `data/bestiary.db` (файл не включён в git/архив проекта) или используйте абсолютный путь. Рекомендуется сначала сделать резервную копию. Отдельный Excel `bestiary_datasets.xlsx` также должен находиться у вас локально; он не включён в архив. Абсолютный путь тоже поддерживается; в Windows-файле `.env` удобнее использовать прямые слеши `/`.

Загрузчик читает:

- `plants` — таксономические карточки (включая scientific_name, family, genus, rank, is_medicinal);
- `plant_names` — русские/common names и aliases;
- `plant_categories` + `categories` — категории;
- `documents` + `sources` — полноценные документы и сведения об источниках;
- `plant_descriptions` + `sources` — описания с разделом, языком и уровнем evidence;
- `plant_uses`, `plant_compounds`, `habitats` + `sources` — заявленные использования, соединения и местообитания с source/evidence metadata.

`plant_images` пока остаётся структурированным каталогом изображений и не индексируется текстовым BM25.

Для поиска BM25 из этих сущностей строится единый корпус в памяти при запуске. Существующая `documents_fts` (FTS5) остаётся в БД, но базовый BM25 в приложении вычисляется собственной реализацией по формуле из презентации. Так сохраняется воспроизводимость учебного задания.

**Ограничение исходной Excel-выгрузки:** поля `description`, `description_language` и `description_source_id` пустые, поэтому 418 таксономических записей дают сведения о названиях/классификации, но не заменяют ботанические описания, данные о токсичности, применении, химических соединениях или местообитании. Флаг `is_medicinal=1` — только метка классификации из набора, а не доказательство эффективности или безопасности. Backend специально маркирует такие записи как `taxonomy_only`.

Импорт Excel выполняется отдельно и не выполняется при каждом старте сервера:

```powershell
# Сначала проверить файл и конфликты, не меняя БД:
python -m backend.scripts.import_taxonomy_xlsx "C:/path/bestiary_datasets.xlsx" --db "C:/path/bestiary.db" --dry-run

# Затем выполнить импорт:
python -m backend.scripts.import_taxonomy_xlsx "C:/path/bestiary_datasets.xlsx" --db "C:/path/bestiary.db"
```

Импортёр обновляет только таксономические колонки в `plants`, не удаляет уже заполненные описания/ссылки в БД, не меняет `documents`, `sources`, `plant_uses`, `plant_compounds`, `habitats` и `plant_images`. Дубликаты ID или научных названий приводят к ошибке вместо тихого слияния. Сделайте резервную копию БД перед импортом.

После импорта включите `DATA_SOURCE=sqlite` и перезапустите backend. Проверка корпуса:

```powershell
python -m backend.scripts.validate_corpus
```

Если база содержит только схему, но ещё не содержит строк в `plants`/`documents`/`plant_descriptions`, загрузчик завершится с понятной ошибкой, а не переключится незаметно на demo-корпус.

Если выбран `DATA_SOURCE=jsonl`, данные находятся в `data/plants.jsonl`, одна JSON-запись на строку. Обязательные поля: `document_id`, `plant_name`, `content`. У каждой записи должны быть источник и метаданные происхождения; `source_url` допускает `null`, если реальной ссылки нет.

JSONL seed-корпус содержит четыре демонстрационных текста с `record_status=demo_unverified`. Они нужны для проверки конвейера и **не являются фактологически проверенной научной базой**. При `DATA_SOURCE=sqlite` объём и полнота данных определяются содержимым вашей БД; taxonomy-only записи нельзя трактовать как описания применения/токсичности. До публикации проверьте лицензии, факты и реальные URL источников.

Реализация обработки:

- нижний регистр, токенизация Unicode-слов; пунктуация отделяется;
- стоп-слова и лемматизация не применяются (как в учебном примере);
- разбиение по предложениям, размер чанка около 900 символов, overlap около 120 символов;
- BM25: `k1=1.2`, `b=0.75` по умолчанию;
- `MIN_BM25_SCORE=0.20` фильтрует очень слабые совпадения. Порог — эвристическая настройка на текущем корпусе, его нужно пересмотреть после наполнения базы;
- индекс строится в памяти при запуске. После редактирования корпуса перезапустите backend.

Формула соответствует презентации:

\[
BM25(q,d)=\sum_{t\in q} IDF(t)\cdot\frac{tf(t,d)(k_1+1)}{tf(t,d)+k_1(1-b+b\cdot |d|/avgdl)}
\]

\[
IDF(t)=\ln\left(1+\frac{N-df(t)+0.5}{df(t)+0.5}\right)
\]

Параметры можно изменить через `BM25_K1`, `BM25_B`, `MIN_BM25_SCORE`. Более подробная схема — `docs/retrieval/corpus-spec.md`.

## 8. Фотоидентификация

Endpoint `/api/v1/identify` проксирует одну фотографию в Pl@ntNet. Требуется `PLANTNET_API_KEY` в `.env`. На текущей реализации разрешены JPEG/PNG, размер одного файла ограничен 10 МБ. Сервис возвращает несколько кандидатов и score от внешнего API. Score не следует считать вероятностью безошибочного определения.

Пользователь должен выбрать кандидата вручную. Только после выбора интерфейс отправляет текстовый вопрос в RAG. Фото не передаётся напрямую LLM, а собственная модель не обучается. При отсутствии PlantNet API key UI сообщает, что фотоидентификация не настроена.

## 9. API

| Метод | Endpoint | Назначение |
|---|---|---|
| `GET` | `/api/v1/health` | состояние backend и статистика корпуса |
| `GET` | `/api/v1/config` | безопасные публичные флаги конфигурации |
| `GET` | `/api/v1/search?q=...&limit=5` | BM25-поиск |
| `POST` | `/api/v1/ask` | RAG / Agentic RAG |
| `GET` | `/api/v1/plants/{document_id}` | карточка растения |
| `POST` | `/api/v1/identify?organ=auto` | фотоидентификация через Pl@ntNet, `multipart/form-data` поле `image` |

Пример запроса:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/ask \\
  -H 'Content-Type: application/json' \\
  -d '{"query":"Венерина мухоловка ловушка створки","limit":5,"agentic":true}'
```

Полные структуры ответов, статусы и ошибки описаны в `docs/architecture/api-contract.md`.

## 10. Проверки и benchmark

```bash
python -m pytest -q
python -m backend.scripts.validate_corpus
python -m backend.scripts.run_benchmark
```

Результаты benchmark по умолчанию сохраняются в `.data-local/benchmark-last.json` (папка исключена из Git). Smoke-набор из четырёх вопросов хранится в `data/benchmark.json`; он **не заменяет** учебное задание на 30 документов, 10 обычных вопросов и 5 вопросов-ловушек. Текущие метрики приведены в `docs/retrieval/benchmark-results-smoke.json` и не являются доказательством качества на полноценной базе.

## 11. Структура репозитория

```text
.
├── index.html, login.html, register.html
├── css/style.css, js/app.js, img/
├── backend/
│   ├── app/                 # FastAPI, конфигурация, corpus, BM25, LLM, RAG
│   ├── tests/               # unit и API tests
│   └── scripts/             # benchmark, corpus validator и Excel importer
├── data/
│   ├── plants.jsonl         # демонстрационный JSONL-корпус
│   ├── bestiary.db          # положить вашу SQLite БД сюда (не включается в Git)
│   └── benchmark.json       # smoke benchmark
├── docs/                    # SDD, архитектура, API, retrieval и тестирование
├── scripts/run-gguf-server.ps1 # локальный запуск ваших GGUF через llama.cpp
├── requirements.txt
├── requirements-semantic.txt # optional dependency только для future dense retrieval
└── .env.example
```

## 12. Известные ограничения

- При DATA_SOURCE=jsonl корпус остаётся демонстрационным (4 записи). При DATA_SOURCE=sqlite используются реальные строки вашей БД; качество зависит от наполненности источниками и описаниями.
- Поиск реализует классический BM25 без лемматизации/стемминга; русские падежные формы могут не совпадать.
- Dense/vector retrieval и hybrid search пока не реализованы; `requirements-semantic.txt` оставлен как опциональная заготовка для последующего этапа.
- Живые вызовы Ollama/llama.cpp/KoboldCpp/внешнего LLM не проверялись без пользовательской конфигурации; tool loop протестирован заглушкой. Tiefighter/Kunoichi рекомендуется использовать без Agentic RAG.
- Живой Pl@ntNet вызов не проверялся без API key.
- История чатов хранится в `localStorage` конкретного браузера; серверная синхронизация и реальные учётные записи не реализованы. Страницы входа/регистрации остаются демонстрационными. Перед публичным развёртыванием нужны аутентификация, rate limiting, политика доступа и наблюдаемость; текущая сборка предназначена для локального/контролируемого запуска.
- Ответы не являются медицинской консультацией, определением съедобности или гарантированной идентификацией растения.

## 13. Документация

Начните с `docs/SDD.md`. Актуальные источники данных описаны в `docs/architecture/sqlite-data-source.md`, локальные GGUF-провайдеры — в `docs/architecture/local-gguf.md`; остальные контракты находятся в `docs/architecture/`, правила корпуса и метрики — в `docs/retrieval/`.
