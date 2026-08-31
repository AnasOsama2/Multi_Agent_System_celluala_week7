"""
Data models shared between the Analyst Agent and the Answer Agent.

Keeping these as plain, framework-agnostic dataclasses lets both agents
(and the Retriever Agent, which is a teammate's task) talk to each other
through a stable, typed contract instead of loose dicts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional


class EvidenceSufficiency(Enum):
    """Outcome of the Analyst's 'Evidence Assessment' decision node."""
    ENOUGH = auto()
    INSUFFICIENT = auto()


class ResponseFormat(Enum):
    """How the Answer Agent should render the final answer."""
    TEXT = auto()
    TABLE = auto()
    MIXED = auto()


@dataclass(frozen=True)
class EvidenceChunk:
    """One retrieved chunk, as produced by the Retriever Agent."""
    document: str
    page: int
    content: str
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def citation_key(self) -> str:
        return f"{self.document}, p.{self.page}"


@dataclass
class ExtractedTable:
    """Structured table pulled out of an EvidenceChunk by the TableExtractorTool."""
    source: EvidenceChunk
    headers: list[str]
    rows: list[list[str]]

    def to_markdown(self) -> str:
        header_line = "| " + " | ".join(self.headers) + " |"
        sep_line = "| " + " | ".join("---" for _ in self.headers) + " |"
        row_lines = ["| " + " | ".join(r) + " |" for r in self.rows]
        return "\n".join([header_line, sep_line, *row_lines])


@dataclass
class ComparisonResult:
    """Output of the DocumentComparisonTool."""
    subject: str
    per_document: dict[str, str]
    similarities: list[str] = field(default_factory=list)
    differences: list[str] = field(default_factory=list)


@dataclass
class AnalysisFinding:
    """One atomic conclusion the Analyst reached, always traceable to evidence."""
    statement: str
    supporting_evidence: list[EvidenceChunk]
    computed_value: Optional[float] = None


@dataclass
class AnalysisResult:
    """
    Everything the Analyst Agent hands to the Answer Agent: the reasoning
    output plus the sufficiency verdict from the Evidence Assessment step.
    """
    question: str
    findings: list[AnalysisFinding]
    sufficiency: EvidenceSufficiency
    tables: list[ExtractedTable] = field(default_factory=list)
    comparisons: list[ComparisonResult] = field(default_factory=list)
    follow_up_query: Optional[str] = None  # set when sufficiency == INSUFFICIENT
    iterations_used: int = 0


@dataclass
class Citation:
    marker: str  # e.g. "[1]"
    document: str
    page: int


@dataclass
class FinalAnswer:
    """What the Answer Agent returns to the user."""
    text: str
    format: ResponseFormat
    citations: list[Citation]
    sources: list[str]
