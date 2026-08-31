"""
Minimal contract the Analyst Agent needs from a Retriever Agent to close
the feedback loop shown in the workflow diagram. The real Retriever Agent
(query rewriting, semantic + keyword search, reranking, ...) is a
teammate's task; this interface is all the Analyst depends on, so any
compliant implementation - or a mock, for testing - can be plugged in.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from models.schemas import EvidenceChunk


class RetrieverInterface(ABC):
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5) -> list[EvidenceChunk]:
        raise NotImplementedError
