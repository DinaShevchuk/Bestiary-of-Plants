"""Import the `plants` taxonomy sheet from bestiary_datasets.xlsx into SQLite.

The importer updates only taxonomy columns. It never overwrites narrative
records, sources, plant uses, compounds, images or descriptions.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

FIELDS = [
    "plant_id", "gbif_taxon_key", "scientific_name", "scientific_name_authorship",
    "family", "genus", "specific_epithet", "taxonomic_status", "kingdom", "rank",
    "description", "description_language", "description_source_id", "is_medicinal",
    "data_status", "created_at", "updated_at",
]
REQUIRED = {"plant_id", "scientific_name", "family", "genus", "specific_epithet", "kingdom", "rank", "is_medicinal", "data_status", "created_at", "updated_at"}


def clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, str):
        value = value.strip()
        return value or None
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xlsx", nargs="?", default="bestiary_datasets.xlsx", help="Path to workbook")
    parser.add_argument("--db", default="data/bestiary.db", help="Target SQLite database")
    parser.add_argument("--sheet", default="plants", help="Worksheet name (default: plants)")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing")
    args = parser.parse_args()

    xlsx_path = Path(args.xlsx).expanduser().resolve()
    db_path = Path(args.db).expanduser().resolve()
    if not xlsx_path.exists():
        raise SystemExit(f"Excel workbook not found: {xlsx_path}")
    if not db_path.exists():
        raise SystemExit(f"SQLite database not found: {db_path}. Create/initialize it before importing.")

    workbook = load_workbook(xlsx_path, read_only=True, data_only=True)
    if args.sheet in workbook.sheetnames:
        worksheet = workbook[args.sheet]
    else:
        worksheet = workbook.worksheets[0]
        print(f"WARNING: worksheet '{args.sheet}' not found; using '{worksheet.title}'.")

    iterator = worksheet.iter_rows(values_only=True)
    try:
        headers = [str(x).strip() if x is not None else "" for x in next(iterator)]
    except StopIteration:
        raise SystemExit("Worksheet is empty.")
    header_index = {name: index for index, name in enumerate(headers) if name}
    missing = sorted(REQUIRED - header_index.keys())
    if missing:
        raise SystemExit(f"Missing required columns: {', '.join(missing)}")

    rows: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    seen_names: dict[str, int] = {}
    skipped_empty = 0
    for row_number, cells in enumerate(iterator, start=2):
        item = {field: clean(cells[index]) if index < len(cells) else None
                for field, index in header_index.items() if field in FIELDS}
        if all(value is None for value in item.values()):
            skipped_empty += 1
            continue
        try:
            plant_id = int(item["plant_id"])
        except (TypeError, ValueError):
            raise SystemExit(f"Invalid plant_id at row {row_number}: {item.get('plant_id')!r}")
        empty_required = [field for field in REQUIRED - {"plant_id", "is_medicinal"} if item.get(field) in (None, "")]
        if empty_required:
            raise SystemExit(f"Missing required values at row {row_number}: {', '.join(sorted(empty_required))}")
        scientific_name = str(item.get("scientific_name") or "").strip()
        if not scientific_name:
            raise SystemExit(f"Empty scientific_name at row {row_number}")
        if plant_id in seen_ids:
            raise SystemExit(f"Duplicate plant_id {plant_id} in Excel (row {row_number})")
        key = scientific_name.casefold()
        if key in seen_names:
            raise SystemExit(f"Duplicate scientific_name '{scientific_name}' in rows {seen_names[key]} and {row_number}; fix the source workbook first.")
        seen_ids.add(plant_id)
        seen_names[key] = row_number
        item["plant_id"] = plant_id
        medicinal = item.get("is_medicinal")
        if medicinal not in (0, 1, "0", "1", False, True):
            raise SystemExit(f"is_medicinal must be 0/1 at row {row_number}; got {medicinal!r}")
        item["is_medicinal"] = int(medicinal)
        item.setdefault("data_status", "duke_taxonomy")
        rows.append(item)

    workbook.close()
    if not rows:
        raise SystemExit("No plant records found in worksheet.")

    report = {"workbook": str(xlsx_path), "sheet": worksheet.title, "records": len(rows),
              "unique_plant_ids": len(seen_ids), "skipped_empty_rows": skipped_empty, "dry_run": args.dry_run}
    conn = sqlite3.connect(db_path)
    try:
        columns = {r[1] for r in conn.execute("PRAGMA table_info(plants)")}
        if not columns:
            raise SystemExit("Target database has no 'plants' table.")
        missing_target = sorted(set(FIELDS) - columns)
        if missing_target:
            raise SystemExit(f"Target plants table lacks columns: {', '.join(missing_target)}")
        if args.dry_run:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        insert_cols = ", ".join(FIELDS)
        placeholders = ", ".join("?" for _ in FIELDS)
        update_cols = [field for field in FIELDS if field != "plant_id"]
        update_sql = ", ".join(f"{field}=COALESCE(excluded.{field}, plants.{field})" for field in update_cols)
        sql = f"INSERT INTO plants ({insert_cols}) VALUES ({placeholders}) ON CONFLICT(plant_id) DO UPDATE SET {update_sql}"
        with conn:
            for item in rows:
                conn.execute(sql, [item.get(field) for field in FIELDS])
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise SystemExit(
            f"Import rolled back because of a database constraint: {exc}. "
            "Check duplicate scientific names (case-insensitive) and foreign keys."
        ) from exc
    finally:
        conn.close()
    report["database"] = str(db_path)
    report["imported_or_updated"] = len(rows)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
