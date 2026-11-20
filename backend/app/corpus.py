
"""Corpus loading and deterministic text chunking for plant records."""
from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+|\n{2,}")


@dataclass(frozen=True)
class PlantDocument:
    document_id: str
    plant_name: str
    content: str
    scientific_name: str | None = None
    aliases: tuple[str, ...] = ()
    category: tuple[str, ...] = ()
    source_title: str = "Источник не указан"
    source_url: str | None = None
    publisher: str | None = None
    published_at: str | None = None
    accessed_at: str | None = None
    language: str = "ru"
    license_or_usage_note: str | None = None
    family: str | None = None
    genus: str | None = None
    specific_epithet: str | None = None
    taxonomic_status: str | None = None
    kingdom: str | None = None
    rank: str | None = None
    is_medicinal: int | None = None
    record_status: str = "unreviewed"
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, item: dict[str, Any]) -> "PlantDocument":
        required = ("document_id", "plant_name", "content")
        missing = [
            name for name in required
            if not str(item.get(name, "")).strip()
        ]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        known = {
            "document_id", "plant_name", "scientific_name", "aliases",
            "category", "content", "source_title", "source_url",
            "publisher", "published_at", "accessed_at", "language",
            "license_or_usage_note", "record_status", "family", "genus",
            "specific_epithet", "taxonomic_status", "kingdom", "rank",
            "is_medicinal",
        }

        aliases = item.get("aliases") or []
        category = item.get("category") or []

        if isinstance(aliases, str):
            aliases = [aliases]
        if isinstance(category, str):
            category = [category]

        return cls(
            document_id=str(item["document_id"]).strip(),
            plant_name=str(item["plant_name"]).strip(),
            scientific_name=_optional_str(item.get("scientific_name")),
            aliases=tuple(str(x).strip() for x in aliases if str(x).strip()),
            category=tuple(str(x).strip() for x in category if str(x).strip()),
            content=str(item["content"]).strip(),
            source_title=str(item.get("source_title") or "Источник не указан"),
            source_url=_optional_str(item.get("source_url")),
            publisher=_optional_str(item.get("publisher")),
            published_at=_optional_str(item.get("published_at")),
            accessed_at=_optional_str(item.get("accessed_at")),
            language=str(item.get("language") or "ru"),
            license_or_usage_note=_optional_str(
                item.get("license_or_usage_note")
            ),
            family=_optional_str(item.get("family")),
            genus=_optional_str(item.get("genus")),
            specific_epithet=_optional_str(item.get("specific_epithet")),
            taxonomic_status=_optional_str(item.get("taxonomic_status")),
            kingdom=_optional_str(item.get("kingdom")),
            rank=_optional_str(item.get("rank")),
            is_medicinal=_optional_int(item.get("is_medicinal")),
            record_status=str(item.get("record_status") or "unreviewed"),
            extra={k: v for k, v in item.items() if k not in known},
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "plant_name": self.plant_name,
            "scientific_name": self.scientific_name,
            "aliases": list(self.aliases),
            "category": list(self.category),
            "content": self.content,
            "source_title": self.source_title,
            "source_url": self.source_url,
            "publisher": self.publisher,
            "published_at": self.published_at,
            "accessed_at": self.accessed_at,
            "language": self.language,
            "license_or_usage_note": self.license_or_usage_note,
            "record_status": self.record_status,
            "family": self.family,
            "genus": self.genus,
            "specific_epithet": self.specific_epithet,
            "taxonomic_status": self.taxonomic_status,
            "kingdom": self.kingdom,
            "rank": self.rank,
            "is_medicinal": self.is_medicinal,
            **self.extra,
        }


def _optional_int(value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_str(value: Any) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    return str(value).strip()


def load_corpus(path: Path) -> list[PlantDocument]:
    if not path.exists():
        return []

    records = []
    seen = set()

    for line_number, raw in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue

        try:
            item = json.loads(raw)
            if not isinstance(item, dict):
                raise ValueError("Each JSONL line must contain a JSON object")
            document = PlantDocument.from_dict(item)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid corpus record at {path}:{line_number}: {exc}"
            ) from exc

        if document.document_id in seen:
            raise ValueError(
                f"Duplicate document_id '{document.document_id}' "
                f"at line {line_number}"
            )

        seen.add(document.document_id)
        records.append(document)

    return records


def load_sqlite_corpus(path: Path) -> list[PlantDocument]:
    """Read the Russian Bestiary-of-Plants SQLite database without modifying it."""

    if not path.exists():
        raise FileNotFoundError(f"SQLite database not found: {path}")

    conn = sqlite3.connect(
        f"file:{path.resolve().as_posix()}?mode=ro",
        uri=True,
    )
    conn.row_factory = sqlite3.Row

    def table_exists(name: str) -> bool:
        return conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone() is not None

    def safe_json_list(value: Any) -> list[str]:
        if not value:
            return []
        try:
            parsed = json.loads(value) if isinstance(value, str) else value
        except (json.JSONDecodeError, TypeError):
            return [str(value).strip()] if str(value).strip() else []

        if isinstance(parsed, str):
            return [parsed.strip()] if parsed.strip() else []
        if isinstance(parsed, list):
            return [
                str(x).strip() for x in parsed
                if x is not None and str(x).strip()
            ]
        return []

    def unique(values: Iterable[Any]) -> list[str]:
        result = []
        seen = set()
        for value in values:
            if value is None:
                continue
            value = str(value).strip()
            if value and value not in seen:
                seen.add(value)
                result.append(value)
        return result

    try:
        if not table_exists("plants"):
            raise ValueError("В базе отсутствует таблица plants.")

        plants = {
            int(row["plant_id"]): dict(row)
            for row in conn.execute("SELECT * FROM plants")
        }

        # Источники
        sources = {}
        if table_exists("sources"):
            sources = {
                int(row["source_id"]): dict(row)
                for row in conn.execute("SELECT * FROM sources")
            }

        def get_source(source_id: Any) -> dict[str, Any]:
            sid = _optional_int(source_id)
            return sources.get(sid, {}) if sid is not None else {}

        # Альтернативные названия растений
        names_by_plant = defaultdict(list)

        if table_exists("plant_names"):
            rows = conn.execute(
                """
                SELECT *
                FROM plant_names
                ORDER BY plant_id, name_type, language, name
                """
            )
            for row in rows:
                item = dict(row)
                names_by_plant[int(item["plant_id"])].append(item)

        # Категории
        categories_by_plant = defaultdict(list)

        if table_exists("plant_categories") and table_exists("categories"):
            rows = conn.execute(
                """
                SELECT pc.plant_id, c.slug, c.name_ru, c.name_en
                FROM plant_categories pc
                JOIN categories c
                    ON c.category_id = pc.category_id
                """
            )
            for row in rows:
                item = dict(row)
                categories_by_plant[int(item["plant_id"])].extend(
                    x for x in (
                        item.get("name_ru"),
                        item.get("slug"),
                        item.get("name_en"),
                    ) if x
                )

        def plant_identity(plant_id: Any):
            pid = _optional_int(plant_id)
            plant = plants.get(pid) if pid is not None else None

            if not plant:
                return (
                    "Неизвестное растение", None, [], [], {},
                )

            names = names_by_plant.get(pid, [])

            russian_names = []
            other_names = []

            for item in names:
                name = item.get("name_ru")
                if name:
                    russian_names.append(name)

                language = str(item.get("language") or "").lower()
                original_name = item.get("name")

                if original_name:
                    if language.startswith("ru"):
                        russian_names.append(original_name)
                    else:
                        other_names.append(original_name)

            preferred = (
                _optional_str(plant.get("name_ru"))
                or next(iter(unique(russian_names)), None)
                or _optional_str(plant.get("scientific_name"))
                or f"Растение {pid}"
            )

            aliases = unique([
                *russian_names,
                *other_names,
                plant.get("scientific_name"),
            ])
            aliases = [x for x in aliases if x != preferred]

            categories = unique(categories_by_plant.get(pid, []))

            return (
                preferred,
                plant.get("scientific_name"),
                aliases,
                categories,
                plant,
            )

        records: list[PlantDocument] = []

        # 1. Таксономические записи
        for plant_id, plant in plants.items():
            name, scientific, aliases, categories, _ = plant_identity(
                plant_id
            )

            family = plant.get("family_ru") or plant.get("family")
            description = plant.get("description_ru") or plant.get("description")

            fields = [
                f"Научное название: {scientific or ''}",
                f"Семейство: {family or ''}",
                f"Род: {plant.get('genus') or ''}",
                f"Видовой эпитет: {plant.get('specific_epithet') or ''}",
                f"Таксономический статус: {plant.get('taxonomic_status') or ''}",
            ]

            content = ". ".join(x for x in fields if not x.endswith(": "))
            if description:
                content += ". Описание: " + str(description)

            content += (
                ". Поле medicinal не подтверждает лечебную эффективность, "
                "безопасность или дозировку."
            )

            source = get_source(plant.get("description_source_id"))

            records.append(PlantDocument(
                document_id=f"plant-taxonomy-{plant_id}",
                plant_name=name,
                scientific_name=scientific,
                aliases=tuple(aliases),
                category=tuple(categories),
                content=content,
                source_title=(
                    source.get("title_ru")
                    or source.get("title")
                    or "Таксономическая запись"
                ),
                source_url=source.get("source_url"),
                publisher=source.get("publisher"),
                accessed_at=source.get("accessed_at"),
                language="ru",
                license_or_usage_note=source.get("license_note"),
                family=family,
                genus=plant.get("genus"),
                specific_epithet=plant.get("specific_epithet"),
                taxonomic_status=plant.get("taxonomic_status"),
                kingdom=plant.get("kingdom"),
                rank=plant.get("rank"),
                is_medicinal=plant.get("is_medicinal"),
                record_status="taxonomy_only",
                extra={
                    "plant_id": plant_id,
                    "data_status": plant.get("data_status"),
                    "source_id": plant.get("description_source_id"),
                },
            ))

        # 2. Основные русскоязычные документы
        if table_exists("documents_ru"):
            for row in conn.execute(
                "SELECT * FROM documents_ru ORDER BY document_id"
            ):
                item = dict(row)
                pid = item.get("plant_id")
                name, scientific, aliases, categories, plant = (
                    plant_identity(pid)
                )

                source = get_source(item.get("source_id"))

                aliases = unique([
                    *aliases,
                    *safe_json_list(item.get("aliases_json")),
                ])
                categories = unique([
                    *categories,
                    *safe_json_list(item.get("categories_json")),
                    *safe_json_list(item.get("categories_ru")),
                ])

                content = str(item.get("content") or "").strip()
                if not content:
                    continue

                records.append(PlantDocument(
                    document_id=f"document-ru-{item['document_id']}",
                    plant_name=item.get("plant_name_ru") or name,
                    scientific_name=item.get("scientific_name") or scientific,
                    aliases=tuple(aliases),
                    category=tuple(categories),
                    content=content,
                    source_title=(
                        item.get("source_title")
                        or source.get("title_ru")
                        or source.get("title")
                        or "Источник не указан"
                    ),
                    source_url=item.get("source_url") or source.get("source_url"),
                    publisher=item.get("publisher") or source.get("publisher"),
                    accessed_at=item.get("accessed_at") or source.get("accessed_at"),
                    language=item.get("language") or "ru",
                    license_or_usage_note=(
                        item.get("license_or_usage_note")
                        or source.get("license_note")
                    ),
                    family=(plant or {}).get("family_ru") or (plant or {}).get("family"),
                    genus=(plant or {}).get("genus"),
                    specific_epithet=(plant or {}).get("specific_epithet"),
                    taxonomic_status=(plant or {}).get("taxonomic_status"),
                    kingdom=(plant or {}).get("kingdom"),
                    rank=(plant or {}).get("rank"),
                    is_medicinal=(plant or {}).get("is_medicinal"),
                    record_status="source_document",
                    extra={
                        "plant_id": pid,
                        "source_id": item.get("source_id"),
                        "original_document_id": item.get("original_document_id"),
                    },
                ))

        # 3. Описания
        if table_exists("plant_descriptions"):
            for row in conn.execute(
                "SELECT * FROM plant_descriptions ORDER BY description_id"
            ):
                item = dict(row)
                pid = item.get("plant_id")

                language = str(item.get("language") or "").lower()
                if language and not language.startswith("ru"):
                    continue

                name, scientific, aliases, categories, plant = (
                    plant_identity(pid)
                )

                description = str(item.get("content") or "").strip()
                if not description:
                    continue

                section = item.get("section") or "Описание"
                source = get_source(item.get("source_id"))

                records.append(PlantDocument(
                    document_id=f"plant-description-{item['description_id']}",
                    plant_name=name,
                    scientific_name=scientific,
                    aliases=tuple(aliases),
                    category=tuple(categories),
                    content=f"Раздел: {section}. {description}",
                    source_title=(
                        source.get("title_ru")
                        or source.get("title")
                        or f"Описание растения: {section}"
                    ),
                    source_url=source.get("source_url"),
                    publisher=source.get("publisher"),
                    accessed_at=source.get("accessed_at"),
                    language="ru",
                    license_or_usage_note=source.get("license_note"),
                    family=(plant or {}).get("family_ru") or (plant or {}).get("family"),
                    genus=(plant or {}).get("genus"),
                    specific_epithet=(plant or {}).get("specific_epithet"),
                    taxonomic_status=(plant or {}).get("taxonomic_status"),
                    kingdom=(plant or {}).get("kingdom"),
                    rank=(plant or {}).get("rank"),
                    is_medicinal=(plant or {}).get("is_medicinal"),
                    record_status=str(item.get("evidence_level") or "source_reported"),
                    extra={
                        "plant_id": pid,
                        "section": section,
                        "source_id": item.get("source_id"),
                        "source_reference": item.get("source_reference"),
                    },
                ))

        # 4. Применения: группируем по растению
        uses_by_plant = defaultdict(list)

        if table_exists("plant_uses"):
            for row in conn.execute(
                "SELECT * FROM plant_uses ORDER BY plant_use_id"
            ):
                item = dict(row)
                pid = _optional_int(item.get("plant_id"))
                if pid is None:
                    continue

                use_text = (
                    item.get("use_text_ru")
                    or item.get("activity_ru")
                    or item.get("use_text")
                    or item.get("activity_en")
                )

                if not use_text:
                    continue

                parts = [str(use_text)]
                if item.get("use_type"):
                    parts.append(f"Тип: {item['use_type']}")
                if item.get("evidence_type"):
                    parts.append(f"Тип свидетельства: {item['evidence_type']}")
                if item.get("country_ru"):
                    parts.append(f"Страна: {item['country_ru']}")
                if item.get("local_name"):
                    parts.append(f"Местное название: {item['local_name']}")

                source = get_source(item.get("source_id"))
                source_info = source.get("title_ru") or source.get("title")

                if source_info:
                    parts.append(f"Источник: {source_info}")
                if item.get("source_reference"):
                    parts.append(f"Библиографическая ссылка: {item['source_reference']}")

                uses_by_plant[pid].append(". ".join(parts))

        for pid, descriptions in uses_by_plant.items():
            name, scientific, aliases, categories, plant = plant_identity(pid)

            records.append(PlantDocument(
                document_id=f"plant-uses-{pid}",
                plant_name=name,
                scientific_name=scientific,
                aliases=tuple(aliases),
                category=tuple(categories),
                content="Сведения об описанных применениях растения:\n"
                        + "\n".join(descriptions),
                source_title="Сведения о применении из базы данных",
                language="ru",
                family=(plant or {}).get("family_ru") or (plant or {}).get("family"),
                genus=(plant or {}).get("genus"),
                specific_epithet=(plant or {}).get("specific_epithet"),
                is_medicinal=(plant or {}).get("is_medicinal"),
                record_status="source_reported",
                extra={"plant_id": pid, "use_count": len(descriptions)},
            ))

        # 5. Химические соединения: группируем по растению
        compounds_by_plant = defaultdict(list)

        if table_exists("plant_compounds") and table_exists("compounds"):
            query = """
                SELECT
                    pc.*,
                    c.name,
                    c.name_ru,
                    c.normalized_name,
                    c.cas_number
                FROM plant_compounds pc
                JOIN compounds c ON c.compound_id = pc.compound_id
                ORDER BY pc.plant_id, pc.compound_id
            """

            for row in conn.execute(query):
                item = dict(row)
                pid = _optional_int(item.get("plant_id"))
                if pid is None:
                    continue

                compound_name = (
                    item.get("name_ru")
                    or item.get("name")
                    or item.get("normalized_name")
                )
                if not compound_name:
                    continue

                parts = [str(compound_name)]

                if item.get("plant_part_ru") or item.get("plant_part"):
                    parts.append(
                        f"Часть растения: "
                        f"{item.get('plant_part_ru') or item.get('plant_part')}"
                    )

                if item.get("compound_class_ru") or item.get("compound_class"):
                    parts.append(
                        f"Класс: "
                        f"{item.get('compound_class_ru') or item.get('compound_class')}"
                    )

                low = item.get("concentration_low_ppm")
                high = item.get("concentration_high_ppm")

                if low is not None or high is not None:
                    parts.append(f"Концентрация: {low}–{high} ppm")

                if item.get("cas_number"):
                    parts.append(f"CAS: {item['cas_number']}")

                compounds_by_plant[pid].append("; ".join(parts))

        for pid, compounds_list in compounds_by_plant.items():
            name, scientific, aliases, categories, plant = plant_identity(pid)

            records.append(PlantDocument(
                document_id=f"plant-compounds-{pid}",
                plant_name=name,
                scientific_name=scientific,
                aliases=tuple(aliases),
                category=tuple(categories),
                content="Химические соединения, указанные в базе:\n"
                        + "\n".join(compounds_list),
                source_title="Сведения о химических соединениях",
                language="ru",
                family=(plant or {}).get("family_ru") or (plant or {}).get("family"),
                genus=(plant or {}).get("genus"),
                specific_epithet=(plant or {}).get("specific_epithet"),
                record_status="source_reported",
                extra={
                    "plant_id": pid,
                    "compound_count": len(compounds_list),
                },
            ))

        # 6. Места произрастания
        if table_exists("habitats"):
            for row in conn.execute(
                "SELECT * FROM habitats ORDER BY habitat_id"
            ):
                item = dict(row)
                pid = item.get("plant_id")
                name, scientific, aliases, categories, plant = (
                    plant_identity(pid)
                )

                fields = [
                    item.get("habitat_description"),
                    f"Местность: {item['locality']}" if item.get("locality") else None,
                    f"Код страны: {item['country_code']}" if item.get("country_code") else None,
                ]
                content = ". ".join(str(x) for x in fields if x)

                if not content:
                    continue

                source = get_source(item.get("source_id"))

                records.append(PlantDocument(
                    document_id=f"plant-habitat-{item['habitat_id']}",
                    plant_name=name,
                    scientific_name=scientific,
                    aliases=tuple(aliases),
                    category=tuple(categories),
                    content=content,
                    source_title=(
                        source.get("title_ru")
                        or source.get("title")
                        or "Источник о местообитании"
                    ),
                    source_url=source.get("source_url"),
                    publisher=source.get("publisher"),
                    accessed_at=source.get("accessed_at"),
                    language="ru",
                    family=(plant or {}).get("family_ru") or (plant or {}).get("family"),
                    genus=(plant or {}).get("genus"),
                    record_status="source_reported",
                    extra={
                        "plant_id": pid,
                        "source_id": item.get("source_id"),
                        "source_reference": item.get("source_reference"),
                    },
                ))

        if not records:
            raise ValueError(
                "Не удалось загрузить записи из SQLite. "
                "Проверь структуру базы и SQLITE_DB_PATH."
            )

        seen = set()
        for record in records:
            if record.document_id in seen:
                raise ValueError(
                    f"Duplicate document_id: {record.document_id}"
                )
            seen.add(record.document_id)

        return records

    finally:
        conn.close()


def load_configured_corpus(
    data_source: str,
    data_file: Path,
    sqlite_db_path: Path,
) -> list[PlantDocument]:
    if data_source.lower() == "sqlite":
        return load_sqlite_corpus(sqlite_db_path)
    return load_corpus(data_file)


def chunk_document(
    document: PlantDocument,
    max_chars: int = 900,
    overlap_chars: int = 120,
) -> list[dict[str, Any]]:
    text = re.sub(r"\s+", " ", document.content).strip()
    if not text:
        return []

    sentences = [
        part.strip()
        for part in SENTENCE_SPLIT.split(text)
        if part.strip()
    ]

    chunks = []
    current = ""

    for sentence in sentences:
        if len(sentence) > max_chars:
            if current:
                chunks.append(current)
                current = ""

            step = max(1, max_chars - overlap_chars)
            for start in range(0, len(sentence), step):
                piece = sentence[start:start + max_chars].strip()
                if piece:
                    chunks.append(piece)
            continue

        candidate = f"{current} {sentence}".strip() if current else sentence

        if current and len(candidate) > max_chars:
            chunks.append(current)
            tail = current[-overlap_chars:].strip() if overlap_chars else ""
            current = f"{tail} {sentence}".strip() if tail else sentence
        else:
            current = candidate

    if current:
        chunks.append(current)

    result = []

    for index, chunk in enumerate(chunks, start=1):
        result.append({
            "chunk_id": f"{document.document_id}#chunk-{index:03d}",
            "document_id": document.document_id,
            "plant_name": document.plant_name,
            "scientific_name": document.scientific_name,
            "aliases": list(document.aliases),
            "category": list(document.category),
            "content": chunk,
            "source_title": document.source_title,
            "source_url": document.source_url,
            "publisher": document.publisher,
            "language": document.language,
            "record_status": document.record_status,
            "family": document.family,
            "genus": document.genus,
            "specific_epithet": document.specific_epithet,
            "taxonomic_status": document.taxonomic_status,
            "kingdom": document.kingdom,
            "rank": document.rank,
            "is_medicinal": document.is_medicinal,
            "extra": dict(document.extra),
        })

    return result


def build_chunks(
    documents: Iterable[PlantDocument],
    max_chars: int = 900,
    overlap_chars: int = 120,
) -> list[dict[str, Any]]:
    chunks = []
    for document in documents:
        chunks.extend(
            chunk_document(
                document,
                max_chars=max_chars,
                overlap_chars=overlap_chars,
            )
        )
    return chunks
