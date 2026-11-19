"""Validate the plant JSONL corpus and report provenance gaps."""
from __future__ import annotations

import argparse
import json
from collections import Counter

from backend.app.config import Settings
from backend.app.corpus import build_chunks, load_configured_corpus


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="fail if any record is not reviewed or has no source URL")
    args = parser.parse_args()

    settings = Settings.from_env()
    documents = load_configured_corpus(settings.data_source, settings.data_file, settings.sqlite_db_path)
    status_counts = Counter(document.record_status for document in documents)
    missing_urls = [document.document_id for document in documents if not document.source_url]
    unreviewed = [document.document_id for document in documents if document.record_status not in {"reviewed", "source_document", "source_reported"}]
    report = {
        "data_source": settings.data_source,
        "file": str(settings.sqlite_db_path if settings.data_source == "sqlite" else settings.data_file),
        "documents": len(documents),
        "chunks": len(build_chunks(documents)),
        "record_status_counts": dict(sorted(status_counts.items())),
        "missing_source_url": missing_urls,
        "not_reviewed": unreviewed,
        "strict_passed": not missing_urls and not unreviewed,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if args.strict and not report["strict_passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
