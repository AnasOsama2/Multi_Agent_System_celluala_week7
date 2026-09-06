"""
Retriever Interface contract for Analyst Agent.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from app.agents.schemas import EvidenceChunk


class RetrieverInterface(ABC):
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5) -> list[EvidenceChunk]:
        raise NotImplementedError
