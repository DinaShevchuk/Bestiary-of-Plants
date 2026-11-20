# Gemini CLI — проект «Бестиарий растений»

Сначала прочитай `AGENTS.md`, `docs/ai/PROJECT_CONTEXT.md`, `docs/ai/WORKFLOW.md` и `docs/ai/DEFINITION_OF_DONE.md`.

Проект содержит HTML/CSS/JS frontend и Python/FastAPI backend. BM25, JSONL corpus loader, RAG, bounded tool-calling Agentic RAG и API интеграция реализованы. Live generation зависит от Ollama/OpenAI-compatible конфигурации; фотоидентификация требует Pl@ntNet API key. Seed corpus состоит из demo_unverified записей. Не преувеличивай качество/проверенность корпуса; сохраняй текущий UI и стек; обновляй SDD, контракты и тесты при изменении поведения.
