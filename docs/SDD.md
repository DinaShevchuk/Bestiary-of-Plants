# SDD — спецификация проекта «Бестиарий растений»

<<<<<<< HEAD
**Версия:** 1.2  
**Статус:** базовая работающая реализация BM25/RAG, FastAPI и интеграции интерфейса; LLM и фотоидентификация подключаются конфигурацией.
=======
**Версия:** 1.1  
**Статус:** базовая спецификация для первой контрольной точки  
**Область:** продукт, интерфейс, архитектура и данные для будущего поиска/ответов по корпусу.
>>>>>>> upstream/main

## 1. Назначение

Этот файл связывает продуктовую цель с требованиями, сценариями, интерфейсом, архитектурой, корпусом, тестами и принятыми решениями. Актуальный код и фактические результаты проверок являются источником истины о статусе реализации.

## 2. Спецификация продукта

Пользователь ищет растение по названию или задаёт вопрос естественным языком. Backend выполняет лексический поиск BM25 по подготовленному корпусу, собирает текстовые фрагменты с метаданными источников и передаёт контекст настроенной LLM для генерации. В agentic режиме модель может вызвать ограниченные инструменты дополнительного поиска. При выключенной LLM доступны BM25 и прозрачный показ найденных выдержек. Фотоидентификация доступна отдельным необязательным путём через Pl@ntNet с подтверждением кандидата пользователем.

Продукт образовательный, не медицинский; он не определяет съедобность и не гарантирует безошибочную идентификацию растения.

## 3. Карта спецификации

| Раздел | Файл | Содержание |
|---|---|---|
<<<<<<< HEAD
| Продукт | `product/product-brief.md` | Ценность, аудитория, сценарии и границы |
| Требования | `product/requirements.md` | FR/NFR и критерии приёмки, включая новые функции |
| Сценарии | `product/user-stories.md` | UC-01…UC-06 |
| Интерфейс | `interface/current-artifacts.md`, `interface/interface-spec.md` | Текущие HTML/CSS/JS и поведение UI |
=======
| Продукт и аудитория | `product/product-brief.md` | Проблема, пользователи, ценность, цели и границы MVP |
| Функциональные и нефункциональные требования | `product/requirements.md` | Проверяемые требования FR/NFR и критерии приёмки |
| Пользовательские сценарии | `product/user-stories.md` | Основной поток и альтернативы |
| Макет и интерфейс | `interface/current-artifacts.md`, `interface/interface-spec.md`, `frontend/current-frontend.md` | Фактические страницы frontend, статический чат и поведение UI |
| Административный интерфейс | `frontend/admin-panel.md` | Демонстрационное управление пользователями и каталогом, ограничения localStorage |
| Общее описание проекта | `project-description.md` | Цель, аудитория, роли, возможности и ограничения текущей версии |
>>>>>>> upstream/main
| Архитектура | `architecture/system-overview.md` | Компоненты и поток запроса |
| SQLite | `architecture/sqlite-data-source.md` | Существующая БД, импорт taxonomy XLSX и runtime mapping |
| GGUF | `architecture/local-gguf.md` | Подключение локальных GGUF через llama.cpp/KoboldCpp |
| API | `architecture/api-contract.md` | Фактические endpoints, body, ответы и ошибки |
| Agentic RAG | `architecture/agentic-rag.md` | Tools, бюджет вызовов и защиты |
| Фотоидентификация | `architecture/image-identification.md` | Pl@ntNet integration и ограничения |
| Корпус | `retrieval/corpus-spec.md` | JSONL/SQLite sources, chunking, BM25 index |
| Benchmark | `retrieval/benchmark.md` и `benchmark-results-smoke.json` | Smoke-набор, метрики и ограничения |
| Проверки | `testing/test-plan.md` | Автотесты и ручные проверки |
| Команда | `team/` | Роли и процесс |
| Решения | `decisions/` | Scope и архитектурные выборы |

## 4. Текущий статус реализации

| Компонент | Статус | Подтверждение |
|---|---|---|
| HTML/CSS/JS чат | Реализован, подключён к API | `index.html`, `js/app.js`, `css/style.css` |
| FastAPI backend | Реализован | `backend/app/main.py` |
| JSONL + SQLite corpus loader + chunking | Реализован; SQLite adapter проверен на тестовой схеме, пользовательская БД ещё не получена | `backend/app/corpus.py` |
| Taxonomy XLSX importer | Реализован; требуется прогнать на реальном файле | `backend/scripts/import_taxonomy_xlsx.py` |
| Самостоятельный BM25 | Реализован | `backend/app/retrieval.py` |
| RAG orchestration | Реализован | `backend/app/service.py` |
| Agentic tool loop | Реализован, проверен fake LLM | `backend/app/service.py`, `backend/tests/test_service.py` |
| Ollama / OpenAI-compatible client (including llama.cpp/KoboldCpp) | Реализован; live provider не проверен без настроек | `backend/app/llm.py` |
| PlantNet proxy | Реализован; требует API key | `backend/app/main.py` |
| Dense/hybrid search | Не реализован | Отдельный future scope |
| Научно проверенный полный корпус | Не готов | Seed corpus помечен `demo_unverified` |
| Real authentication/server-side chat history | Не реализовано | Login/register пока демонстрационные; history в localStorage |

## 5. Трассировка требований

| Требование | Сценарий | Компонент | Проверка |
|---|---|---|---|
| FR-01…FR-04 | UC-01 | UI, API, BM25 | `test_api.py`, BM25 tests |
| FR-05…FR-07 | UC-02, UC-03 | Retrieval, RAG, LLM | `test_service.py`, smoke benchmark |
| FR-08…FR-09 | UC-02 | UI/API | Ручной тест loading/error |
| FR-11 | UC-03 | Prompt + safe response policy | Regression questions and manual model review |
| FR-13 | UC-06 | Agentic service/tools | Fake LLM tool-loop test |
| FR-14 | UC-02 | LLM adapter/config | Live Ollama/API check in configured environment |
| FR-15 | UC-05 | PlantNet + upload UI | Endpoint unconfigured test; live provider requires key |
| NFR-03/NFR-07 | UC-02/UC-06 | Chunk metadata, source refs, budget | Service tests |

<<<<<<< HEAD
## 6. Изменение требований
=======
## 5. Текущее состояние frontend и административной панели

Frontend содержит страницу чата, формы входа/регистрации и демонстрационную панель администратора. Чат использует заранее подготовленные ответы и не вызывает backend. Административная панель выполняет операции над демонстрационными пользователями и растениями в `localStorage`; серверная авторизация и проверка роли не реализованы. Подробности и ручные проверки: `frontend/current-frontend.md` и `frontend/admin-panel.md`.

## 6. Процесс изменения требований
>>>>>>> upstream/main

1. Обновить профильный документ и связанный сценарий.
2. Проверить влияние на API, корпус, retrieval и UI.
3. Реализовать и добавить тест.
4. Повторить smoke benchmark для retrieval изменений.
5. Обновить README и связанную документацию.
6. Не менять статус на «реализовано и проверено» без фактической проверки.

<<<<<<< HEAD
## 7. Критерии готовности текущего технического этапа
=======
## 7. Что считается готовым для первой точки
>>>>>>> upstream/main

- API запускается по README и отдаёт текущий frontend;
- BM25 search и `/ask` возвращают фактические chunks и source metadata;
- при отсутствии подходящего контекста возвращается `insufficient_data`;
- без LLM используется `retrieval_only`, не имитирующий генерацию;
- Agentic RAG выполняет только allowlisted tools и уважает hard caps;
- ключи хранятся на backend;
- автотесты запускаются, smoke benchmark воспроизводим;
- документация соответствует фактическим путям и поведению.

Полный этап качества корпуса остаётся незавершённым: seed-набор требует проверки и расширения до целевого benchmark.
