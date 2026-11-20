# Подключение реляционной SQLite-базы

**Статус:** реализован read-only adapter для retrieval и отдельный импорт таксономической Excel-выгрузки.

## Источники и ответственность

- `bestiary.db` — каноническая runtime-БД проекта.
- `bestiary_datasets.xlsx` — исходная выгрузка таксономии; импортируется в `plants`, не читается на каждый вопрос.
- `data/plants.jsonl` — демо-источник для разработки и smoke-тестов.

В `.env` выбирается один источник:

```dotenv
DATA_SOURCE=sqlite
SQLITE_DB_PATH=data/bestiary.db
```

или `DATA_SOURCE=jsonl` для JSONL.

## Таблицы, используемые adapter-ом

| Таблица | Использование |
|---|---|
| `plants` | Таксономическая карточка: научное имя, авторство, семейство, род, эпитет, ранг, kingdom, is_medicinal, data_status |
| `plant_names` | Русские и другие common names, синонимы/aliases |
| `categories`, `plant_categories` | Категории растения |
| `documents` | Документированный текст с title, source, language, aliases/categories и связью на растение |
| `plant_descriptions` | Разделы описания с language, evidence_level, source_reference |
| `sources` | Название публикации, publisher, URL, лицензия, дата доступа |
| `plant_uses` | Заявленные/описанные варианты использования с типом evidence и source |
| `compounds`, `plant_compounds` | Соединения, часть растения, диапазон концентрации, CAS и source |
| `habitats` | Локалитет, страна, описание местообитания и source |

`documents_fts` (FTS5) и триггеры остаются частью SQLite-схемы. Текущий baseline BM25 всё же строится собственным кодом `backend/app/retrieval.py`, а не вызывает FTS5 `bm25()`, чтобы не подменять самостоятельную реализацию, предусмотренную учебной презентацией.

## Как создаются индексируемые записи

1. Каждая строка `plants` создаёт карточку `plant-taxonomy-{plant_id}`. Она содержит только фактически заполненные таксономические поля и явное предупреждение: `is_medicinal` — классификационный флаг, не утверждение об эффективности/безопасности.
2. Каждая строка `documents` становится отдельным документом с наследованием таксономии и алиасов растения. URL из `documents.source_url` имеет приоритет, далее используется URL из `sources`.
3. Каждая строка `plant_descriptions` становится отдельным документом `plant-description-{description_id}` с названием раздела и источником.
4. Документы разбиваются на chunks текущим chunker; BM25 индексирует plant names, scientific names, aliases, categories, family/genus/rank и текст.
5. Источники без URL не получают выдуманный URL. Они возвращаются как source title без hyperlink.

`get_plant_profile` предпочитает source-bearing описание/документ taxonomy-only карточке.

## Excel import

```powershell
python -m backend.scripts.import_taxonomy_xlsx "C:/path/bestiary_datasets.xlsx" --db "C:/path/bestiary.db" --dry-run
python -m backend.scripts.import_taxonomy_xlsx "C:/path/bestiary_datasets.xlsx" --db "C:/path/bestiary.db"
```

Importer:

- выбирает лист по имени `plants` (если отсутствует, берёт первый лист и пишет warning);
- проверяет обязательные поля, уникальность `plant_id` и case-insensitive уникальность `scientific_name` в самом xlsx;
- принимает `is_medicinal` только как 0/1;
- выполняет upsert по `plant_id` в транзакции;
- обновляет только taxonomy-поля, использует `COALESCE` при обновлении, поэтому пустые Excel ячейки не очищают существующие enriched values;
- при конфликте уникального индекса SQLite откатывает транзакцию;
- не изменяет `documents`, `sources`, `plant_descriptions`, `plant_uses`, `plant_compounds`, `habitats` и `plant_images`.

Перед импортом сделайте backup базы. При артефактных названиях сначала проверьте конфликт: автоматическая нормализация или переименование научных названий не производится.

## Ограничения и смысл данных

- Если в xlsx пусты `description`, `description_language`, `description_source_id`, то xlsx даёт таксономию, а не описания растения.
- `is_medicinal=1` само по себе не подтверждает доказанность лечебного эффекта, безопасность или возможность употребления.
- Пустые поля `gbif_taxon_key`/`taxonomic_status` остаются пустыми; adapter не восстанавливает их из интернета.
- `plant_uses`, `plant_compounds` и `habitats` уже входят в текстовую выдачу как отдельные source-reported документы. `plant_images` пока остаётся вне текстового BM25 retrieval.
- Для `plant_uses` / `plant_compounds` / `habitats` LLM должна формулировать факты как сведения, сообщённые конкретным источником, не превращая их в клинические или safety claims.

## Runtime и диагностика

SQLite открывается в read-only режиме. BM25 индекс собирается в памяти при старте процесса. После Excel import или изменения источников перезапустите FastAPI, затем проверьте:

```powershell
python -m backend.scripts.validate_corpus
python -m backend.scripts.run_benchmark
```

Если база отсутствует, не имеет `plants` или не содержит ни одной записи, backend завершится с понятным сообщением, не переключаясь скрытно на демо-корпус.
