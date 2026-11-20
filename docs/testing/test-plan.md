# План проверок

**Статус:** backend unit/API tests реализованы; browser E2E и live provider tests требуют отдельной среды.

## 1. Автоматические проверки

Из корня репозитория:

```bash
python -m compileall -q backend
python -m pytest -q
python -m backend.scripts.validate_corpus
python -m backend.scripts.run_benchmark
node --check js/app.js  # если Node.js установлен
```

Автотесты покрывают:

- Unicode tokenization, отсутствие результатов, BM25 ranking и per-term explain;
- chunking, JSONL record validation, SQLite mapping (taxonomy/documents/descriptions/uses/compounds/habitats) и сохранение source metadata;
- загрузку seed-корпуса, поиск по научному имени/alias;
- `retrieval_only` при отключённой LLM;
- отказ при отсутствии подтверждающих материалов;
- agentic tool cycle с fake LLM и source refs;
- FastAPI health/search/ask/validation, disabled identification и проверку сигнатуры загружаемого файла.

Последний прогон в среде разработки: **22 теста прошли** (`python -m pytest -q`). Повторяйте проверки после изменений; этот текст не заменяет текущий вывод CI.

## 2. Smoke benchmark

```bash
python -m backend.scripts.run_benchmark --output .data-local/benchmark-last.json
```

Текущий четырёхвопросный набор и сохранённые показатели описаны в `../retrieval/benchmark.md` и `../retrieval/benchmark-results-smoke.json`. Он не заменяет полный 30-doc / 10-answerable / 5-trap dataset.

## 3. Ручные проверки UI

1. Запустить FastAPI по README и открыть `/`.
2. Убедиться, что строка статуса показывает backend connected.
3. Отправить точную форму названия из seed corpus, например «Венерина мухоловка».
4. Проверить ответ/выдержки, source refs и пометку demo_unverified.
5. Отправить вопрос вне корпуса и проверить `insufficient_data`.
6. Выключить backend и проверить понятное сообщение об ошибке.
7. Создать несколько чатов, переключиться и обновить страницу — проверить `localStorage`.
8. Проверить мобильную ширину и клавиатурную навигацию.

## 4. LLM provider checks

В локально настроенной среде отдельно выполнить:

- `LLM_PROVIDER=ollama` с моделью, поддерживающей tool calling;
- `LLM_PROVIDER=openai_compatible` с реальным API key для cloud или без key для loopback llama.cpp/KoboldCpp;
- запрос, где модель вызывает `search_plant_knowledge`;
- вопрос с недостаточным контекстом;
- запрос, где модель должна прекратить дополнительные вызовы после лимита.

Live provider calls в текущей сборочной среде не выполнялись; fake LLM test проверяет только orchestration contract.

## 5. Photo identification checks

- Без `PLANTNET_API_KEY` `POST /api/v1/identify` должен вернуть `503`.
- С ключом загрузить JPEG и PNG менее 10 MB; убедиться, что получаются кандидаты.
- Передать пустой/неподдерживаемый файл и файл больше лимита.
- Подтвердить кандидата вручную и проверить, что далее вызывается внутренний `/ask`.
- Live Pl@ntNet вызов не выполнен без пользовательского ключа.

## 6. Безопасность и достоверность

- проверить, что `.env` исключён из Git, а `/api/v1/config` не раскрывает ключи;
- проверить отсутствие fictitious source URL;
- проверить prompt, запрещающий выполнение инструкций из документа;
- провести ручную safety regression оценку реальной LLM по вопросам об употреблении и лечении;
- не считать demo_unverified запись надёжным научным источником.
