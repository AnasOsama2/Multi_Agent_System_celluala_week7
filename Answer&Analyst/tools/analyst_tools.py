"""
Tools owned by the Analyst Agent: Calculator, Table Extractor,
Document Comparison, Data Analysis, and Search/Retrieve More Evidence.
"""
from __future__ import annotations

import re
import statistics
from typing import Any

from agents.base import Tool, ToolExecutionError
from agents.retriever_interface import RetrieverInterface
from llm.client import LLMClient
from models.schemas import ComparisonResult, EvidenceChunk, ExtractedTable


def _product(values: list[float]) -> float:
    result = 1.0
    for v in values:
        result *= v
    return result


def _divide(values: list[float]) -> float:
    if values[1] == 0:
        raise ToolExecutionError("division by zero")
    return values[0] / values[1]


class CalculatorTool(Tool):
    """Exact arithmetic/statistics so the Analyst never eyeballs numbers."""

    name = "calculator"
    description = "Perform arithmetic and basic statistics over a list of numbers."

    _OPS = {
        "add": lambda v: sum(v),
        "subtract": lambda v: v[0] - sum(v[1:]),
        "multiply": lambda v: _product(v),
        "divide": lambda v: _divide(v),
        "average": lambda v: statistics.fmean(v),
        "percentage": lambda v: (v[0] / v[1]) * 100,
        "ratio": lambda v: v[0] / v[1],
        "min": lambda v: min(v),
        "max": lambda v: max(v),
        "median": lambda v: statistics.median(v),
        "stdev": lambda v: statistics.pstdev(v),
    }

    def run(self, *, operation: str, values: list[float]) -> float:
        if not values:
            raise ToolExecutionError("calculator requires at least one value")
        if operation not in self._OPS:
            raise ToolExecutionError(
                f"Unknown operation '{operation}'. Valid: {sorted(self._OPS)}"
            )
        return round(self._OPS[operation](values), 6)


class TableExtractorTool(Tool):
    """
    Pulls a structured table out of an evidence chunk's raw text.
    Handles the common '|'-delimited and whitespace-aligned layouts that
    PDF-to-text extraction tends to produce; falls back to a single-column
    table if no tabular structure is detected.
    """

    name = "table_extractor"
    description = "Extract a structured (headers + rows) table from an evidence chunk."

    def run(self, *, chunk: EvidenceChunk) -> ExtractedTable:
        lines = [ln.strip() for ln in chunk.content.splitlines() if ln.strip()]
        if not lines:
            raise ToolExecutionError("chunk has no content to extract a table from")

        if any("|" in ln for ln in lines):
            rows = [
                [cell.strip() for cell in ln.strip("|").split("|")]
                for ln in lines
                if not re.fullmatch(r"[\s|:-]+", ln)
            ]
        else:
            rows = [re.split(r"\s{2,}|\t", ln) for ln in lines]

        if len(rows) < 2:
            return ExtractedTable(source=chunk, headers=["content"], rows=[[chunk.content]])

        headers, *body = rows
        width = len(headers)
        body = [r for r in body if len(r) == width]
        return ExtractedTable(source=chunk, headers=headers, rows=body)


class DocumentComparisonTool(Tool):
    """
    Groups evidence by source document and asks the LLM to reason about
    similarities/differences - the Analyst supplies the subject, the tool
    handles grouping and prompt construction.
    """

    name = "document_comparison"
    description = "Compare how multiple documents address the same subject."

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def run(self, *, subject: str, chunks: list[EvidenceChunk]) -> ComparisonResult:
        if not chunks:
            raise ToolExecutionError("document_comparison requires at least one evidence chunk")

        per_document: dict[str, list[str]] = {}
        for c in chunks:
            per_document.setdefault(c.document, []).append(c.content)
        merged = {doc: " ".join(texts) for doc, texts in per_document.items()}

        prompt = _comparison_prompt(subject, merged)
        raw = self._llm.complete(prompt)
        similarities, differences = _split_comparison_response(raw)

        return ComparisonResult(
            subject=subject,
            per_document=merged,
            similarities=similarities,
            differences=differences,
        )


def _comparison_prompt(subject: str, per_document: dict[str, str]) -> str:
    docs_block = "\n\n".join(f"[{doc}]\n{text}" for doc, text in per_document.items())
    return (
        f"Compare the following documents on '{subject}'. "
        "List similarities on one line prefixed 'SIMILARITIES:' and "
        "differences on another prefixed 'DIFFERENCES:', semicolon-separated.\n\n"
        f"{docs_block}"
    )


def _split_comparison_response(raw: str) -> tuple[list[str], list[str]]:
    similarities: list[str] = []
    differences: list[str] = []
    for line in raw.splitlines():
        if line.upper().startswith("SIMILARITIES:"):
            similarities = [s.strip() for s in line.split(":", 1)[1].split(";") if s.strip()]
        elif line.upper().startswith("DIFFERENCES:"):
            differences = [s.strip() for s in line.split(":", 1)[1].split(";") if s.strip()]
    return similarities, differences


class DataAnalysisTool(Tool):
    """
    Higher-level numeric analysis (rankings, distributions, trend
    direction) built on top of CalculatorTool - composition over
    duplication.
    """

    name = "data_analysis"
    description = "Rank, summarize, or find trends across a labelled set of numeric values."

    def __init__(self, calculator: CalculatorTool | None = None) -> None:
        self._calculator = calculator or CalculatorTool()

    def run(self, *, data: dict[str, float], mode: str = "rank") -> Any:
        if not data:
            raise ToolExecutionError("data_analysis requires at least one data point")

        values = list(data.values())
        if mode == "rank":
            return sorted(data.items(), key=lambda kv: kv[1], reverse=True)
        if mode == "summary":
            return {
                "average": self._calculator.run(operation="average", values=values),
                "min": self._calculator.run(operation="min", values=values),
                "max": self._calculator.run(operation="max", values=values),
                "stdev": self._calculator.run(operation="stdev", values=values) if len(values) > 1 else 0.0,
            }
        if mode == "trend":
            ordered = list(data.values())
            if len(ordered) < 2:
                return "insufficient data"
            delta = ordered[-1] - ordered[0]
            return "increasing" if delta > 0 else "decreasing" if delta < 0 else "flat"
        raise ToolExecutionError(f"Unknown mode '{mode}'. Valid: rank, summary, trend")


class RetrieveMoreEvidenceTool(Tool):
    """
    The Analyst's half of the feedback loop: hands a refined query back to
    the Retriever Agent when the Evidence Assessment step decides the
    current evidence is insufficient.
    """

    name = "retrieve_more_evidence"
    description = "Ask the Retriever Agent for additional, more specific evidence."

    def __init__(self, retriever: RetrieverInterface) -> None:
        self._retriever = retriever

    def run(self, *, query: str, top_k: int = 5) -> list[EvidenceChunk]:
        return self._retriever.retrieve(query, top_k=top_k)
