import sqlite3
from pathlib import Path

from backend.app.corpus import load_sqlite_corpus, build_chunks
from backend.app.retrieval import BM25Index


def create_db(path: Path):
    conn = sqlite3.connect(path)
    conn.executescript("""
    CREATE TABLE plants (
      plant_id INTEGER PRIMARY KEY,
      gbif_taxon_key INTEGER,
      scientific_name TEXT NOT NULL,
      scientific_name_authorship TEXT,
      family TEXT,
      genus TEXT,
      specific_epithet TEXT,
      taxonomic_status TEXT,
      kingdom TEXT,
      rank TEXT,
      description TEXT,
      description_language TEXT,
      description_source_id INTEGER,
      is_medicinal INTEGER NOT NULL,
      data_status TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
    CREATE TABLE plant_names (
      plant_name_id INTEGER PRIMARY KEY,
      plant_id INTEGER, name TEXT, language TEXT, name_type TEXT, source_id INTEGER
    );
    CREATE TABLE sources (
      source_id INTEGER PRIMARY KEY, source_key TEXT, title TEXT, publisher TEXT,
      source_url TEXT, license_note TEXT, accessed_at TEXT, notes TEXT
    );
    CREATE TABLE documents (
      document_id TEXT PRIMARY KEY, plant_id INTEGER, plant_name TEXT, scientific_name TEXT,
      aliases_json TEXT, categories_json TEXT, content TEXT, source_id INTEGER,
      source_title TEXT, source_url TEXT, publisher TEXT, published_at TEXT,
      accessed_at TEXT, language TEXT, license_or_usage_note TEXT,
      parent_document_id TEXT, chunk_index INTEGER, created_at TEXT
    );
    CREATE TABLE plant_descriptions (
      description_id INTEGER PRIMARY KEY, plant_id INTEGER, section TEXT, content TEXT,
      language TEXT, source_id INTEGER, source_reference TEXT, evidence_level TEXT
    );
    CREATE TABLE plant_uses (
      plant_use_id INTEGER PRIMARY KEY, plant_id INTEGER, use_text TEXT, use_type TEXT,
      evidence_type TEXT, source_id INTEGER, source_reference TEXT
    );
    CREATE TABLE compounds (
      compound_id INTEGER PRIMARY KEY, name TEXT NOT NULL, normalized_name TEXT NOT NULL,
      cas_number TEXT
    );
    CREATE TABLE plant_compounds (
      plant_id INTEGER, compound_id INTEGER, plant_part TEXT,
      concentration_low_ppm REAL, concentration_high_ppm REAL, compound_class TEXT,
      source_id INTEGER, source_reference TEXT
    );
    CREATE TABLE habitats (
      habitat_id INTEGER PRIMARY KEY, plant_id INTEGER, locality TEXT, country_code TEXT,
      habitat_description TEXT, source_id INTEGER, source_reference TEXT
    );
    INSERT INTO plants VALUES (1, NULL, 'Abelmoschus esculentus', '(L.) MOENCH',
      'Malvaceae', 'Abelmoschus', 'esculentus', NULL, 'Plantae', 'SPECIES',
      NULL, NULL, NULL, 1, 'duke_taxonomy', '2026-11-19', '2026-11-19');
    INSERT INTO plant_names VALUES (1, 1, 'Бамия', 'ru', 'common', NULL);
    INSERT INTO sources VALUES (1, 'source-1', 'Ботаническое описание', 'Publisher',
      'https://example.org/plant', 'license unknown', '2026-11-20', NULL);
    INSERT INTO documents VALUES ('doc-1', 1, 'Бамия', 'Abelmoschus esculentus',
      '["окра"]', '["овощные"]', 'Растение выращивают как овощную культуру.',
      1, 'Ботаническое описание', NULL, NULL, NULL, NULL, 'ru', NULL, NULL, 0, 'now');
    INSERT INTO plant_descriptions VALUES (1, 1, 'Описание', 'Культура теплолюбива.', 'ru', 1,
      'section 2', 'source_reported');
    INSERT INTO plant_uses VALUES (1, 1, 'Используется как пищевой продукт.', 'food',
      'reported', 1, 'section 3');
    INSERT INTO compounds VALUES (5, 'Quercetin', 'quercetin', '117-39-5');
    INSERT INTO plant_compounds VALUES (1, 5, 'leaf', 10.0, 25.0, 'flavonoid', 1, 'table 2');
    INSERT INTO habitats VALUES (1, 1, 'Cultivated fields', 'IN', 'Warm cultivated habitats.', 1, 'section 4');
    """)
    conn.commit()
    conn.close()


def test_load_sqlite_includes_taxonomy_documents_and_descriptions(tmp_path):
    db = tmp_path / "bestiary.db"
    create_db(db)
    docs = load_sqlite_corpus(db)

    by_id = {doc.document_id: doc for doc in docs}
    taxonomy = by_id["plant-taxonomy-1"]
    assert taxonomy.plant_name == "Бамия"
    assert taxonomy.scientific_name == "Abelmoschus esculentus"
    assert taxonomy.family == "Malvaceae"
    assert taxonomy.is_medicinal == 1
    assert "не подтверждает" in taxonomy.content

    doc = by_id["doc-1"]
    assert "окра" in doc.aliases
    assert doc.source_url == "https://example.org/plant"
    assert doc.family == "Malvaceae"

    desc = by_id["plant-description-1"]
    assert "Культура теплолюбива" in desc.content
    assert desc.source_url == "https://example.org/plant"
    use = by_id["plant-use-1"]
    assert "Используется как пищевой продукт" in use.content
    compound = next(doc for doc in docs if doc.document_id.startswith("plant-compound-1-5-"))
    assert "117-39-5" in compound.content
    assert "10.0–25.0 ppm" in compound.content
    habitat = by_id["plant-habitat-1"]
    assert "Warm cultivated habitats" in habitat.content

    chunks = build_chunks(docs)
    hits = BM25Index(chunks).search("Бамия семейство Malvaceae", 5)
    assert hits
    assert any(hit["document_id"] == "plant-taxonomy-1" for hit in hits)


def test_load_sqlite_missing_file_is_clear(tmp_path):
    missing = tmp_path / "missing.db"
    try:
        load_sqlite_corpus(missing)
    except FileNotFoundError as exc:
        assert "SQLite database not found" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError")
