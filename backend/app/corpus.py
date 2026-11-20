"""Corpus loading and deterministic text chunking for plant records."""
from __future__ import annotations

import json
import re
import sqlite3
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
        missing = [name for name in required if not str(item.get(name, "")).strip()]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        known = {
            "document_id", "plant_name", "scientific_name", "aliases", "category", "content",
            "source_title", "source_url", "publisher", "published_at", "accessed_at", "language",
            "license_or_usage_note", "record_status", "family", "genus", "specific_epithet",
            "taxonomic_status", "kingdom", "rank", "is_medicinal",
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
            source_title=str(item.get("source_title") or "Источник не указан").strip(),
            source_url=_optional_str(item.get("source_url")),
            publisher=_optional_str(item.get("publisher")),
            published_at=_optional_str(item.get("published_at")),
            accessed_at=_optional_str(item.get("accessed_at")),
            language=str(item.get("language") or "ru").strip(),
            license_or_usage_note=_optional_str(item.get("license_or_usage_note")),
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
    records: list[PlantDocument] = []
    seen: set[str] = set()
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        try:
            item = json.loads(raw)
            if not isinstance(item, dict):
                raise ValueError("Each JSONL line must contain a JSON object")
            document = PlantDocument.from_dict(item)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid corpus record at {path}:{line_number}: {exc}") from exc
        if document.document_id in seen:
            raise ValueError(f"Duplicate document_id '{document.document_id}' at line {line_number}")
        seen.add(document.document_id)
        records.append(document)
    return records



def load_sqlite_corpus(path: Path) -> list[PlantDocument]:
    """Load searchable records from the project's relational SQLite schema.

    Reads taxonomy from plants and narrative material from documents and
    plant_descriptions. It does not infer missing facts or invent source URLs.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"SQLite database not found: {path}. Set SQLITE_DB_PATH or place bestiary.db in data/."
        )

    def table_exists(conn: sqlite3.Connection, name: str) -> bool:
        return conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone() is not None

    def safe_json_list(value: Any) -> list[str]:
        if value is None:
            return []
        try:
            parsed = json.loads(value) if isinstance(value, str) else value
        except (json.JSONDecodeError, TypeError):
            return [str(value)] if str(value).strip() else []
        if isinstance(parsed, str):
            return [parsed] if parsed.strip() else []
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
        return []

    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        if not table_exists(conn, "plants"):
            raise ValueError("SQLite schema does not contain required table 'plants'.")

        plants = {int(row["plant_id"]): dict(row) for row in conn.execute("SELECT * FROM plants")}
        names_by_plant: dict[int, list[dict[str, Any]]] = {}
        if table_exists(conn, "plant_names"):
            for row in conn.execute("SELECT * FROM plant_names ORDER BY plant_id, name_type, language, name"):
                item = dict(row)
                names_by_plant.setdefault(int(item["plant_id"]), []).append(item)

        categories_by_plant: dict[int, list[str]] = {}
        if table_exists(conn, "plant_categories") and table_exists(conn, "categories"):
            for row in conn.execute(
                """SELECT pc.plant_id, c.slug, c.name_ru, c.name_en
                   FROM plant_categories pc JOIN categories c ON c.category_id=pc.category_id"""
            ):
                item = dict(row)
                categories_by_plant.setdefault(int(item["plant_id"]), []).extend(
                    x for x in (item.get("slug"), item.get("name_ru"), item.get("name_en")) if x
                )

        sources: dict[int, dict[str, Any]] = {}
        if table_exists(conn, "sources"):
            sources = {int(row["source_id"]): dict(row) for row in conn.execute("SELECT * FROM sources")}

        def plant_identity(plant_id: int | None, fallback_name: str | None = None) -> tuple[str, str | None, list[str], list[str], dict[str, Any]]:
            plant = plants.get(int(plant_id)) if plant_id is not None else None
            if not plant:
                name = (fallback_name or "Неизвестное растение").strip()
                return name, None, [], [], {}
            names = names_by_plant.get(int(plant_id), [])
            ru_common = [x["name"] for x in names if x.get("name") and (x.get("language") or "").lower().startswith("ru")]
            common = [x["name"] for x in names if x.get("name") and x.get("name_type", "common") == "common"]
            all_names = list(dict.fromkeys(x["name"] for x in names if x.get("name")))
            preferred = (ru_common or common or all_names or [plant.get("scientific_name") or fallback_name or f"Растение {plant_id}"])[0]
            aliases = [x for x in all_names if x != preferred]
            categories = list(dict.fromkeys(categories_by_plant.get(int(plant_id), [])))
            return str(preferred), plant.get("scientific_name"), aliases, categories, plant

        records: list[PlantDocument] = []

        # A taxonomy-only card makes scientific names/families searchable, but
        # explicitly states that it contains no pharmacological/safety evidence.
        for plant_id, plant in plants.items():
            plant_name, scientific_name, aliases, categories, _ = plant_identity(plant_id)
            fields = [
                ("Научное название", scientific_name),
                ("Авторство научного названия", plant.get("scientific_name_authorship")),
                ("Семейство", plant.get("family")),
                ("Род", plant.get("genus")),
                ("Видовой эпитет", plant.get("specific_epithet")),
                ("Таксономический статус", plant.get("taxonomic_status")),
                ("Царство", plant.get("kingdom")),
                ("Ранг", plant.get("rank")),
            ]
            content = "Таксономическая запись. " + "; ".join(f"{label}: {value}" for label, value in fields if value not in (None, "")) + ". "
            medicinal = plant.get("is_medicinal")
            content += (
                f"Флаг is_medicinal: {medicinal}. Это только значение классификационного поля исходного набора; "
                "оно не подтверждает лечебную эффективность, безопасность, дозировку или способ применения. "
            )
            if plant.get("description"):
                content += "Описание из поля plants.description: " + str(plant["description"])
            content += "В этой записи нет подтверждённых сведений о токсичности, съедобности, применении или противопоказаниях, если они не приведены отдельно в источниках."
            source_id = plant.get("description_source_id")
            source = sources.get(int(source_id)) if source_id else None
            records.append(PlantDocument(
                document_id=f"plant-taxonomy-{plant_id}",
                plant_name=plant_name,
                scientific_name=scientific_name,
                aliases=tuple(aliases),
                category=tuple(categories),
                content=content,
                source_title=(source or {}).get("title") or f"Таксономическая запись ({plant.get('data_status') or 'taxonomy_only'})",
                source_url=(source or {}).get("source_url"),
                publisher=(source or {}).get("publisher"),
                accessed_at=(source or {}).get("accessed_at"),
                language=plant.get("description_language") or "en",
                license_or_usage_note=(source or {}).get("license_note") or "Таксономические поля; первичная ссылка и лицензия не указаны в записи.",
                family=plant.get("family"), genus=plant.get("genus"),
                specific_epithet=plant.get("specific_epithet"), taxonomic_status=plant.get("taxonomic_status"),
                kingdom=plant.get("kingdom"), rank=plant.get("rank"), is_medicinal=medicinal,
                record_status="taxonomy_only",
                extra={"plant_id": plant_id, "data_status": plant.get("data_status"), "source_id": source_id},
            ))

        if table_exists(conn, "documents"):
            for row in conn.execute("SELECT * FROM documents ORDER BY document_id"):
                item = dict(row)
                plant_id = item.get("plant_id")
                plant_name, taxonomy_name, db_aliases, db_categories, plant = plant_identity(plant_id, item.get("plant_name"))
                source = sources.get(int(item["source_id"])) if item.get("source_id") is not None else {}
                aliases = list(dict.fromkeys([*db_aliases, *safe_json_list(item.get("aliases_json"))]))
                categories = list(dict.fromkeys([*db_categories, *safe_json_list(item.get("categories_json"))]))
                records.append(PlantDocument(
                    document_id=str(item["document_id"]),
                    plant_name=str(item.get("plant_name") or plant_name),
                    scientific_name=item.get("scientific_name") or taxonomy_name,
                    aliases=tuple(aliases), category=tuple(categories),
                    content=str(item.get("content") or ""),
                    source_title=str(item.get("source_title") or (source or {}).get("title") or "Источник не указан"),
                    source_url=item.get("source_url") or (source or {}).get("source_url"),
                    publisher=item.get("publisher") or (source or {}).get("publisher"),
                    published_at=item.get("published_at"),
                    accessed_at=item.get("accessed_at") or (source or {}).get("accessed_at"),
                    language=item.get("language") or "en",
                    license_or_usage_note=item.get("license_or_usage_note") or (source or {}).get("license_note"),
                    family=(plant or {}).get("family"), genus=(plant or {}).get("genus"),
                    specific_epithet=(plant or {}).get("specific_epithet"),
                    taxonomic_status=(plant or {}).get("taxonomic_status"), kingdom=(plant or {}).get("kingdom"),
                    rank=(plant or {}).get("rank"), is_medicinal=(plant or {}).get("is_medicinal"),
                    record_status="source_document",
                    extra={"plant_id": plant_id, "source_id": item.get("source_id"),
                           "parent_document_id": item.get("parent_document_id"), "chunk_index": item.get("chunk_index")},
                ))

        if table_exists(conn, "plant_descriptions"):
            query = "SELECT * FROM plant_descriptions ORDER BY description_id"
            for row in conn.execute(query):
                item = dict(row)
                plant_id = int(item["plant_id"])
                plant_name, scientific_name, aliases, categories, plant = plant_identity(plant_id)
                source = sources.get(int(item["source_id"])) if item.get("source_id") is not None else {}
                section = str(item.get("section") or "Описание")
                records.append(PlantDocument(
                    document_id=f"plant-description-{item['description_id']}",
                    plant_name=plant_name, scientific_name=scientific_name,
                    aliases=tuple(aliases), category=tuple(categories),
                    content=f"Раздел: {section}. {item.get('content') or ''}",
                    source_title=(source or {}).get("title") or f"Описание растения: {section}",
                    source_url=(source or {}).get("source_url"),
                    publisher=(source or {}).get("publisher"),
                    accessed_at=(source or {}).get("accessed_at"),
                    language=item.get("language") or "ru",
                    license_or_usage_note=(source or {}).get("license_note"),
                    family=(plant or {}).get("family"), genus=(plant or {}).get("genus"),
                    specific_epithet=(plant or {}).get("specific_epithet"),
                    taxonomic_status=(plant or {}).get("taxonomic_status"), kingdom=(plant or {}).get("kingdom"),
                    rank=(plant or {}).get("rank"), is_medicinal=(plant or {}).get("is_medicinal"),
                    record_status=str(item.get("evidence_level") or "source_reported"),
                    extra={"plant_id": plant_id, "section": section, "source_id": item.get("source_id"),
                           "source_reference": item.get("source_reference")},
                ))

        if table_exists(conn, "plant_uses"):
            for row in conn.execute("SELECT * FROM plant_uses ORDER BY plant_use_id"):
                item = dict(row)
                plant_id = int(item["plant_id"])
                plant_name, scientific_name, aliases, categories, plant = plant_identity(plant_id)
                source = sources.get(int(item["source_id"])) if item.get("source_id") is not None else {}
                fields = [f"Заявленное/описанное использование в источнике: {item.get('use_text') or ''}"]
                if item.get("use_type"):
                    fields.append(f"Тип использования: {item['use_type']}")
                if item.get("evidence_type"):
                    fields.append(f"Тип свидетельства в записи: {item['evidence_type']}")
                records.append(PlantDocument(
                    document_id=f"plant-use-{item['plant_use_id']}",
                    plant_name=plant_name, scientific_name=scientific_name,
                    aliases=tuple(aliases), category=tuple(categories), content=". ".join(fields) + ".",
                    source_title=(source or {}).get("title") or "Источник для записи об использовании не указан",
                    source_url=(source or {}).get("source_url"), publisher=(source or {}).get("publisher"),
                    accessed_at=(source or {}).get("accessed_at"),
                    license_or_usage_note=(source or {}).get("license_note"),
                    family=(plant or {}).get("family"), genus=(plant or {}).get("genus"),
                    specific_epithet=(plant or {}).get("specific_epithet"),
                    taxonomic_status=(plant or {}).get("taxonomic_status"), kingdom=(plant or {}).get("kingdom"),
                    rank=(plant or {}).get("rank"), is_medicinal=(plant or {}).get("is_medicinal"),
                    record_status="source_reported",
                    extra={"plant_id": plant_id, "use_type": item.get("use_type"),
                           "evidence_type": item.get("evidence_type"), "source_id": item.get("source_id"),
                           "source_reference": item.get("source_reference")},
                ))

        if table_exists(conn, "plant_compounds") and table_exists(conn, "compounds"):
            for row in conn.execute(
                """SELECT pc.*, c.name AS compound_name, c.normalized_name, c.cas_number
                   FROM plant_compounds pc JOIN compounds c ON c.compound_id=pc.compound_id
                   ORDER BY pc.plant_id, c.name"""
            ):
                item = dict(row)
                plant_id = int(item["plant_id"])
                plant_name, scientific_name, aliases, categories, plant = plant_identity(plant_id)
                source = sources.get(int(item["source_id"])) if item.get("source_id") is not None else {}
                compound_parts = [f"Соединение, указанное в источнике: {item.get('compound_name') or ''}"]
                if item.get("normalized_name"):
                    compound_parts.append(f"Нормализованное название: {item['normalized_name']}")
                if item.get("cas_number"):
                    compound_parts.append(f"CAS: {item['cas_number']}")
                if item.get("plant_part"):
                    compound_parts.append(f"Часть растения: {item['plant_part']}")
                low, high = item.get("concentration_low_ppm"), item.get("concentration_high_ppm")
                if low is not None or high is not None:
                    if low is not None and high is not None:
                        concentration = f"{low}–{high} ppm"
                    else:
                        concentration = f"{low if low is not None else high} ppm"
                    compound_parts.append(f"Указанная концентрация: {concentration}")
                if item.get("compound_class"):
                    compound_parts.append(f"Класс соединения: {item['compound_class']}")
                records.append(PlantDocument(
                    document_id=f"plant-compound-{plant_id}-{item['compound_id']}-{item.get('source_id')}-{len(records)}",
                    plant_name=plant_name, scientific_name=scientific_name,
                    aliases=tuple(aliases), category=tuple(categories), content=". ".join(compound_parts) + ".",
                    source_title=(source or {}).get("title") or "Источник данных о соединении не указан",
                    source_url=(source or {}).get("source_url"), publisher=(source or {}).get("publisher"),
                    accessed_at=(source or {}).get("accessed_at"),
                    license_or_usage_note=(source or {}).get("license_note"),
                    family=(plant or {}).get("family"), genus=(plant or {}).get("genus"),
                    specific_epithet=(plant or {}).get("specific_epithet"),
                    taxonomic_status=(plant or {}).get("taxonomic_status"), kingdom=(plant or {}).get("kingdom"),
                    rank=(plant or {}).get("rank"), is_medicinal=(plant or {}).get("is_medicinal"),
                    record_status="source_reported",
                    extra={"plant_id": plant_id, "compound_id": item.get("compound_id"),
                           "compound_name": item.get("compound_name"), "plant_part": item.get("plant_part"),
                           "source_id": item.get("source_id"), "source_reference": item.get("source_reference")},
                ))

        if table_exists(conn, "habitats"):
            for row in conn.execute("SELECT * FROM habitats ORDER BY habitat_id"):
                item = dict(row)
                plant_id = int(item["plant_id"])
                plant_name, scientific_name, aliases, categories, plant = plant_identity(plant_id)
                source = sources.get(int(item["source_id"])) if item.get("source_id") is not None else {}
                fields = [f"Описание местообитания из источника: {item.get('habitat_description') or ''}"]
                if item.get("locality"):
                    fields.append(f"Локалитет: {item['locality']}")
                if item.get("country_code"):
                    fields.append(f"Код страны: {item['country_code']}")
                records.append(PlantDocument(
                    document_id=f"plant-habitat-{item['habitat_id']}",
                    plant_name=plant_name, scientific_name=scientific_name,
                    aliases=tuple(aliases), category=tuple(categories), content=". ".join(fields) + ".",
                    source_title=(source or {}).get("title") or "Источник данных о местообитании не указан",
                    source_url=(source or {}).get("source_url"), publisher=(source or {}).get("publisher"),
                    accessed_at=(source or {}).get("accessed_at"),
                    license_or_usage_note=(source or {}).get("license_note"),
                    family=(plant or {}).get("family"), genus=(plant or {}).get("genus"),
                    specific_epithet=(plant or {}).get("specific_epithet"),
                    taxonomic_status=(plant or {}).get("taxonomic_status"), kingdom=(plant or {}).get("kingdom"),
                    rank=(plant or {}).get("rank"), is_medicinal=(plant or {}).get("is_medicinal"),
                    record_status="source_reported",
                    extra={"plant_id": plant_id, "locality": item.get("locality"),
                           "country_code": item.get("country_code"), "source_id": item.get("source_id"),
                           "source_reference": item.get("source_reference")},
                ))

        # A project may export only a schema with no row data. Fail clearly rather
        # than silently using an unrelated JSONL demo corpus.
        if not records:
            raise ValueError(
                "SQLite database contains no plant rows/documents/descriptions. "
                "Check whether bestiary.db has been populated."
            )

        # Duplicate IDs can occur if the database has multiple duplicate rows; detect them.
        seen: set[str] = set()
        for record in records:
            if record.document_id in seen:
                raise ValueError(f"Duplicate document_id in SQLite corpus: {record.document_id}")
            seen.add(record.document_id)
        return records
    finally:
        conn.close()


def load_configured_corpus(data_source: str, data_file: Path, sqlite_db_path: Path) -> list[PlantDocument]:
    """Load corpus from the selected configured source."""
    if data_source == "sqlite":
        return load_sqlite_corpus(sqlite_db_path)
    return load_corpus(data_file)

def chunk_document(document: PlantDocument, max_chars: int = 900, overlap_chars: int = 120) -> list[dict[str, Any]]:
    """Split content on sentence/paragraph boundaries and carry small overlap."""
    text = re.sub(r"\s+", " ", document.content).strip()
    if not text:
        return []
    sentences = [part.strip() for part in SENTENCE_SPLIT.split(text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            for start in range(0, len(sentence), max(1, max_chars - overlap_chars)):
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

    result: list[dict[str, Any]] = []
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


def build_chunks(documents: Iterable[PlantDocument], max_chars: int = 900, overlap_chars: int = 120) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for document in documents:
        chunks.extend(chunk_document(document, max_chars=max_chars, overlap_chars=overlap_chars))
    return chunks
