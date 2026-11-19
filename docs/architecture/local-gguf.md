# Локальные GGUF-модели

**Статус:** OpenAI-compatible клиент backend поддерживает локальные сервера. Совместимость конкретной модели и её tool calling проверяется в окружении пользователя.

## Принцип

`.gguf` файл — это веса модели, а не HTTP endpoint. Backend не загружает GGUF напрямую. Отдельный inference server (llama.cpp `llama-server` или KoboldCpp) загружает файл и открывает HTTP endpoint `/v1/chat/completions`.

## llama.cpp server — рекомендуемый путь

Пример установки на Windows:

```powershell
winget install -e --id ggml.llamacpp
```

После установки откройте новое окно PowerShell. Проверьте, что сервер доступен: `Get-Command llama-server.exe`. Для удобства в репозитории есть скрипт, который находит модель по префиксу имени в Faraday-папке и запускает сервер:

```powershell
.\scripts\run-gguf-server.ps1 -Model kunoichi
# или
.\scripts\run-gguf-server.ps1 -Model tiefighter
```

Пример запуска Kunoichi:

```powershell
llama-server.exe -m "$env:APPDATA\faraday\models\mistral.7b.kunoichi.gguf_v2.q4_k_m" --alias bestiary-kunoichi --host 127.0.0.1 --port 8080 --ctx-size 4096 --n-gpu-layers 0
```

Пример запуска Tiefighter:

```powershell
llama-server.exe -m "$env:APPDATA\faraday\models\llama2.13b.tiefighter.gguf_v2.q4_k_m.gguf" --alias bestiary-tiefighter --host 127.0.0.1 --port 8080 --ctx-size 4096 --n-gpu-layers 0
```

Имя файла сверяйте через `Get-ChildItem "$env:APPDATA\faraday\models"`. Путь в команде должен совпадать с точным именем, включая расширение `.gguf`, если оно действительно есть. Параметр `--n-gpu-layers 0` оставляет вычисления на CPU; при наличии GPU и подходящей сборки llama.cpp количество слоёв можно повышать в пределах свободной VRAM.

`.env`:

```dotenv
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://127.0.0.1:8080/v1
LLM_MODEL=bestiary-kunoichi
LLM_API_KEY=
AGENTIC_ENABLED=false
AGENT_MAX_TOOL_CALLS=0
MAX_CONTEXT_CHARS=6000
```

При переключении на Tiefighter измените `LLM_MODEL` и перезапустите server/backend. Текущий backend разрешает пустой API key только для loopback (`localhost`, `127.0.0.1`, `::1`); для удалённых OpenAI-compatible сервисов ключ всё ещё требуется.

Проверка:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/v1/models
```

## KoboldCpp — альтернативный путь

```powershell
koboldcpp.exe --model "$env:APPDATA\faraday\models\mistral.7b.kunoichi.gguf_v2.q4_k_m" --host 127.0.0.1 --port 5001 --contextsize 4096
```

`.env`:

```dotenv
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://127.0.0.1:5001/v1
LLM_MODEL=local-model
LLM_API_KEY=
AGENTIC_ENABLED=false
```

KoboldCpp принимает любое значение model id для обычной модели (он использует уже загруженные веса). Для OpenAI-compatible режима документирован URL `/v1`.

## Оценка двух моделей

- LLaMA 2 13B Tiefighter Q4_K_M и Mistral 7B Kunoichi Q4_K_M технически загружаются llama.cpp/KoboldCpp как GGUF.
- Их разумно проверить на обычном RAG: retrieval остаётся в backend, модели передаются только отобранные выдержки.
- Это старые roleplay/fine-tune модели; они не являются надёжной основой для function calling. Agentic RAG по умолчанию отключён в примерах.
- Квантизация Q4_K_M — компромисс размера/качества, не гарантия высокого качества ответов.
- Начните с context 4096, низкой температуры и ограниченного числа retrieved chunks. Контекст и GPU layers подбирайте по реальной RAM/VRAM и latency.
- Ответы по растениям могут быть выдуманными даже при наличии хорошего prompt. Поэтому citations, refusal behavior и benchmark должны оставаться включёнными.

## Безопасность

Слушайте только `127.0.0.1`, если endpoint нужен приложению на том же компьютере. Не открывайте API в LAN/Internet без пароля, firewall и явного обоснования. Не коммитьте `.env` или персональные пути/ключи.
