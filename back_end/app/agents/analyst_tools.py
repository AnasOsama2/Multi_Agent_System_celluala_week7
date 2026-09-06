"""
Tools owned by the Analyst Agent: Calculator, Table Extractor,
Document Comparison, Data Analysis, and RetrieveMoreEvidence.
"""
from __future__ import annotations

import re
import statistics
from typing import Any

from app.agents.base import Tool, ToolExecutionError
from app.agents.retriever_interface import RetrieverInterface
from app.agents.llm_adapter import LLMClient
from app.agents.schemas import ComparisonResult, EvidenceChunk, ExtractedTable


def _product(values: list[float]) -> float:
    result = 1.0
    for v in values:
        result *= v
    return result


def _divide(values: list[float]) -> float:
    if len(values) < 2:
        raise ToolExecutionError("division requires at least two values")
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
    Pulls a structured table out of an evidence chunk's raw text or SQL markdown.
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
    Groups evidence by source document and uses the LLM to analyze similarities and differences.
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
    Higher-level numeric analysis (rankings, distributions, trend direction)
    built on top of CalculatorTool.
    """

    name = "data_analysis"
    description = "Rank, summarize, or find trends across a labelled set of numeric values."

    def __init__(self, calculator: CalculatorTool | None = None) -> None:
        self._calculator = calculator or CalculatorTool()

    def run(self, *, data: dict[str, float], mode: str = "summary") -> dict[str, Any]:
        if not data:
            raise ToolExecutionError("data_analysis requires a non-empty data dictionary")

        values = list(data.values())

        if mode == "rank":
            sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)
            return {
                "ranking": [{"label": k, "value": v, "rank": i + 1} for i, (k, v) in enumerate(sorted_items)]
            }

        if mode == "summary":
            return {
                "count": len(values),
                "min": self._calculator.run(operation="min", values=values),
                "max": self._calculator.run(operation="max", values=values),
                "average": self._calculator.run(operation="average", values=values),
                "median": self._calculator.run(operation="median", values=values),
            }

        if mode == "trend":
            if len(values) < 2:
                return {"trend": "insufficient_data"}
            delta = values[-1] - values[0]
            direction = "upward" if delta > 0 else ("downward" if delta < 0 else "flat")
            return {"trend": direction, "delta": delta}

        raise ToolExecutionError(f"Unknown mode '{mode}'. Valid modes: 'summary', 'rank', 'trend'")


class RetrieveMoreEvidenceTool(Tool):
    """Bridges the Analyst back to the Retriever Agent to fetch additional evidence."""

    name = "retrieve_more_evidence"
    description = "Ask the Retriever Agent for more evidence on a specific sub-query."

    def __init__(self, retriever: RetrieverInterface) -> None:
        self._retriever = retriever

    def run(self, *, query: str, top_k: int = 5) -> list[EvidenceChunk]:
        return self._retriever.retrieve(query, top_k=top_k)
