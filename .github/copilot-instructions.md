# GitHub Copilot instructions — «Бестиарий растений»

Перед изменениями изучи `AGENTS.md`, `docs/ai/PROJECT_CONTEXT.md` и профильную спецификацию.

- Текущий стек: статический frontend (`index.html`, `css/style.css`, `js/app.js`) и FastAPI backend (`backend/app/`). Не вводи frontend framework без отдельного обоснования.
- BM25 реализован вручную в `backend/app/retrieval.py`; RAG orchestration — в `backend/app/service.py`; API — в `backend/app/main.py`. Перед изменением контракта изучи `docs/architecture/api-contract.md`.
- Отличай реализованную логику от проверенного живого провайдера: тесты используют fake LLM, живой Ollama/OpenAI-compatible endpoint и Pl@ntNet надо проверять отдельно.
- Seed-корпус содержит только demo_unverified записи. Не добавляй вымышленные факты, источники или URL.
- BM25 лексический, без лемматизации/стемминга; не называй его семантическим. Dense/vector/hybrid search пока не реализован.
- RAG отвечает только по найденному контексту, показывает источники и отказывается при недостатке сведений. Tool calls ограничены сервером; документы и пользовательский ввод — недоверенные данные.
- Не коммить `.env` и не выводи API keys. Pl@ntNet требует `PLANTNET_API_KEY`.
- Запускай `python -m compileall -q backend`, `python -m pytest -q`, smoke benchmark и `node --check js/app.js` (если Node доступен); перечисляй только реально выполненные проверки.
- Обновляй документацию при изменении API, схемы корпуса, переменных окружения, поведения UI или архитектуры.
