import sqlite3
import sys
from pathlib import Path

from openpyxl import Workbook

from backend.scripts import import_taxonomy_xlsx

FIELDS = [
    "plant_id", "gbif_taxon_key", "scientific_name", "scientific_name_authorship",
    "family", "genus", "specific_epithet", "taxonomic_status", "kingdom", "rank",
    "description", "description_language", "description_source_id", "is_medicinal",
    "data_status", "created_at", "updated_at",
]


def make_book(path: Path, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "plants"
    ws.append(FIELDS)
    for row in rows:
        ws.append([row.get(field) for field in FIELDS])
    wb.save(path)


def make_db(path: Path):
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE plants (
        plant_id INTEGER PRIMARY KEY, gbif_taxon_key INTEGER UNIQUE,
        scientific_name TEXT NOT NULL, scientific_name_authorship TEXT,
        family TEXT, genus TEXT, specific_epithet TEXT, taxonomic_status TEXT,
        kingdom TEXT, rank TEXT, description TEXT, description_language TEXT,
        description_source_id INTEGER, is_medicinal INTEGER NOT NULL,
        data_status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    )""")
    conn.execute("""INSERT INTO plants VALUES (
        1, NULL, 'Abelmoschus esculentus', NULL, 'Malvaceae', 'Abelmoschus',
        'esculentus', NULL, 'Plantae', 'SPECIES', 'Existing trusted description',
        'en', NULL, 1, 'existing', '2026-01-01', '2026-01-01'
    )""")
    conn.commit()
    conn.close()


def sample_row(**overrides):
    row = {
        "plant_id": 1, "scientific_name": "Abelmoschus esculentus",
        "family": "Malvaceae", "genus": "Abelmoschus", "specific_epithet": "esculentus",
        "kingdom": "Plantae", "rank": "SPECIES", "is_medicinal": 1,
        "data_status": "duke_taxonomy", "created_at": "2026-11-19 20:26:45",
        "updated_at": "2026-11-19 20:26:45",
    }
    row.update(overrides)
    return row


def run_import(monkeypatch, xlsx: Path, db: Path, *args):
    monkeypatch.setattr(sys, "argv", ["import_taxonomy_xlsx", str(xlsx), "--db", str(db), *args])
    return import_taxonomy_xlsx.main()


def test_import_upserts_taxonomy_and_preserves_enriched_description(tmp_path, monkeypatch):
    db = tmp_path / "bestiary.db"
    xlsx = tmp_path / "bestiary_datasets.xlsx"
    make_db(db)
    make_book(xlsx, [sample_row(family="Malvaceae", description=None, description_language=None)])

    assert run_import(monkeypatch, xlsx, db) == 0
    conn = sqlite3.connect(db)
    row = conn.execute("SELECT family, data_status, description, description_language FROM plants WHERE plant_id=1").fetchone()
    conn.close()
    assert row == ("Malvaceae", "duke_taxonomy", "Existing trusted description", "en")


def test_import_dry_run_does_not_write(tmp_path, monkeypatch):
    db = tmp_path / "bestiary.db"
    xlsx = tmp_path / "bestiary_datasets.xlsx"
    make_db(db)
    make_book(xlsx, [sample_row(family="New family")])

    assert run_import(monkeypatch, xlsx, db, "--dry-run") == 0
    conn = sqlite3.connect(db)
    family = conn.execute("SELECT family FROM plants WHERE plant_id=1").fetchone()[0]
    conn.close()
    assert family == "Malvaceae"


def test_import_rejects_duplicate_scientific_names(tmp_path, monkeypatch):
    db = tmp_path / "bestiary.db"
    xlsx = tmp_path / "bestiary_datasets.xlsx"
    make_db(db)
    make_book(xlsx, [
        sample_row(plant_id=1),
        sample_row(plant_id=2),
    ])

    try:
        run_import(monkeypatch, xlsx, db)
    except SystemExit as exc:
        assert "Duplicate scientific_name" in str(exc)
    else:
        raise AssertionError("Expected duplicate scientific_name validation to fail")
