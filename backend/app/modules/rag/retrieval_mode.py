"""Retrieval strategies shared by RAG, the API and persisted chat history."""

from enum import Enum


class RetrievalMode(str, Enum):
    DENSE = "dense"
    BM25 = "bm25"
    HYBRID = "hybrid"
