import pytest

from backend.app.corpus import PlantDocument, build_chunks, chunk_document, load_corpus
from backend.app.retrieval import BM25Index, tokens


def _docs():
    return [
        {"chunk_id": "a", "document_id": "a", "plant_name": "Венерина мухоловка", "content": "Ловушка состоит из двух створок."},
        {"chunk_id": "b", "document_id": "b", "plant_name": "Росянка", "content": "Листья покрыты липкими волосками."},
        {"chunk_id": "c", "document_id": "c", "plant_name": "Непентес", "content": "Ловчие органы имеют форму кувшина."},
    ]


def test_tokenizer_lowercases_and_keeps_cyrillic_latin():
    assert tokens("Dionaea MUSCIPULA, Венерина-мухоловка!") == [
        "dionaea", "muscipula", "венерина", "мухоловка"
    ]


def test_bm25_returns_matching_documents_in_rank_order():
    index = BM25Index(_docs())
    results = index.search("липкие волоски росянка", limit=3)
    assert results
    assert results[0]["document_id"] == "b"
    assert results[0]["score"] > 0


def test_bm25_empty_and_unknown_queries_return_no_results():
    index = BM25Index(_docs())
    assert index.search("   ") == []
    assert index.search("терминкоторогонет") == []


def test_explain_contains_per_term_contributions():
    index = BM25Index(_docs())
    hit = index.search("липкими волосками", 1)[0]
    explanation = index.explain("липкими волосками", hit)
    assert explanation["score"] > 0
    assert {x["term"] for x in explanation["terms"]} == {"липкими", "волосками"}


def test_chunking_preserves_source_and_splits_long_text():
    plant = PlantDocument.from_dict({
        "document_id": "plant-test", "plant_name": "Тестовое растение",
        "content": "Первое предложение. " + ("Длинное описание. " * 100),
        "source_title": "Тестовый источник", "record_status": "test"
    })
    chunks = chunk_document(plant, max_chars=120, overlap_chars=20)
    assert len(chunks) > 1
    assert chunks[0]["document_id"] == "plant-test"
    assert all(chunk["source_title"] == "Тестовый источник" for chunk in chunks)
    assert chunks[0]["chunk_id"].endswith("001")


def test_build_chunks_returns_empty_for_empty_corpus():
    assert build_chunks([]) == []


def test_corpus_loader_rejects_non_object_jsonl_record(tmp_path):
    path = tmp_path / "invalid.jsonl"
    path.write_text('["not", "an", "object"]\n', encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        load_corpus(path)
