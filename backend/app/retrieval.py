"""A transparent, from-scratch BM25 implementation (lecture formula)."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any, Iterable

# Keep Cyrillic and Latin names, digits and underscore; punctuation is a separator.
TOKEN_RE = re.compile(r"[\w]+", flags=re.UNICODE)


def tokens(text: str) -> list[str]:
    """Lowercase/tokenize text. No stop-word removal or lemmatization by default."""
    return TOKEN_RE.findall((text or "").lower())


class BM25Index:
    def __init__(self, documents: Iterable[dict[str, Any]], k1: float = 1.2, b: float = 0.75):
        self.documents = list(documents)
        self.k1 = float(k1)
        self.b = float(b)
        self.index: dict[str, dict[int, int]] = defaultdict(dict)
        self.lengths: list[int] = []
        self._build()

    def _build(self) -> None:
        self.index.clear()
        self.lengths.clear()
        for doc_index, document in enumerate(self.documents):
            searchable = " ".join([
                str(document.get("plant_name", "")),
                str(document.get("scientific_name") or ""),
                " ".join(document.get("aliases") or []),
                " ".join(document.get("category") or []),
                str(document.get("family") or ""),
                str(document.get("genus") or ""),
                str(document.get("specific_epithet") or ""),
                str(document.get("taxonomic_status") or ""),
                str(document.get("kingdom") or ""),
                str(document.get("rank") or ""),
                str(document.get("content", "")),
            ])
            words = tokens(searchable)
            self.lengths.append(len(words))
            counts = Counter(words)
            for word, term_frequency in counts.items():
                self.index[word][doc_index] = term_frequency
        self.average_length = sum(self.lengths) / len(self.lengths) if self.lengths else 0.0

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        query_words = list(dict.fromkeys(tokens(query)))
        if not query_words or not self.documents or not self.average_length:
            return []
        scores: dict[int, float] = defaultdict(float)
        n_docs = len(self.documents)
        for word in query_words:
            postings = self.index.get(word, {})
            df = len(postings)
            if not df:
                continue
            idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
            for doc_index, tf in postings.items():
                doc_length = self.lengths[doc_index]
                norm = self.k1 * (1 - self.b + self.b * doc_length / self.average_length)
                scores[doc_index] += idf * tf * (self.k1 + 1) / (tf + norm)
        ranked = sorted(scores, key=lambda i: (-scores[i], str(self.documents[i].get("chunk_id", i))))
        results: list[dict[str, Any]] = []
        for index in ranked[:max(0, limit)]:
            if scores[index] <= 0:
                continue
            results.append({**self.documents[index], "score": round(scores[index], 6)})
        return results

    def explain(self, query: str, document: dict[str, Any]) -> dict[str, Any]:
        """Return per-term contributions to make BM25 scores inspectable."""
        doc_index = next((i for i, item in enumerate(self.documents)
                          if item.get("chunk_id") == document.get("chunk_id")), None)
        if doc_index is None or not self.documents or not self.average_length:
            return {"score": 0.0, "terms": []}
        term_details = []
        for word in dict.fromkeys(tokens(query)):
            postings = self.index.get(word, {})
            tf = postings.get(doc_index, 0)
            if not tf:
                continue
            df = len(postings)
            idf = math.log(1 + (len(self.documents) - df + 0.5) / (df + 0.5))
            norm = self.k1 * (1 - self.b + self.b * self.lengths[doc_index] / self.average_length)
            contribution = idf * tf * (self.k1 + 1) / (tf + norm)
            term_details.append({"term": word, "tf": tf, "df": df, "idf": round(idf, 6), "contribution": round(contribution, 6)})
        return {"score": round(sum(x["contribution"] for x in term_details), 6), "terms": term_details}

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "indexed_chunks": len(self.documents),
            "indexed_terms": len(self.index),
            "average_chunk_length": round(self.average_length, 2),
            "k1": self.k1,
            "b": self.b,
        }
