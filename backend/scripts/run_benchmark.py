"""Run the local retrieval smoke benchmark and store machine-readable metrics."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config import Settings
from backend.app.service import PlantKnowledgeService


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=ROOT / "data" / "benchmark.json")
    parser.add_argument("--output", type=Path, default=ROOT / ".data-local" / "benchmark-last.json")
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()

    benchmark = json.loads(args.benchmark.read_text(encoding="utf-8"))
    service = PlantKnowledgeService(Settings.from_env())
    report = []
    recalls, precisions, reciprocal_ranks, abstentions = [], [], [], []
    for case in benchmark["cases"]:
        results = service.search(case["query"], max(1, min(args.k, 10)))
        ranked_ids = list(dict.fromkeys(item["document_id"] for item in results))
        expected = set(case.get("expected_doc_ids", []))
        found = [doc_id for doc_id in ranked_ids if doc_id in expected]
        if expected:
            recall = len(found) / len(expected)
            precision = len(found) / args.k
            rank = next((i for i, doc_id in enumerate(ranked_ids[:args.k], start=1) if doc_id in expected), None)
            rr = 1 / rank if rank else 0.0
            recalls.append(recall)
            precisions.append(precision)
            reciprocal_ranks.append(rr)
            abstention = None
        else:
            recall = precision = rr = None
            abstention = not bool(ranked_ids)
            abstentions.append(float(abstention))
        report.append({
            "query_id": case["query_id"], "query": case["query"],
            "ranked_doc_ids": ranked_ids[:args.k], "expected_doc_ids": sorted(expected),
            f"recall_at_{args.k}": recall, f"precision_at_{args.k}": precision,
            f"reciprocal_rank_at_{args.k}": rr, "abstention_correct": abstention,
        })
    summary = {
        "benchmark_version": benchmark.get("version"),
        "retrieval": "bm25",
        "corpus": service.stats(),
        "k": args.k,
        "mean_recall": sum(recalls) / len(recalls) if recalls else None,
        "mean_precision": sum(precisions) / len(precisions) if precisions else None,
        "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else None,
        "correct_abstention_rate": sum(abstentions) / len(abstentions) if abstentions else None,
        "cases": report,
        "note": "Smoke benchmark only; not a full or human-validated evaluation.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
