"""
Tools owned by the Answer Agent: Citation Formatter, Source Formatter,
and Response Formatter.
"""
from __future__ import annotations

from app.agents.base import Tool, ToolExecutionError
from app.agents.schemas import AnalysisFinding, Citation, ExtractedTable, ResponseFormat


class CitationFormatterTool(Tool):
    """Turns the evidence behind each finding into numbered, de-duplicated citations."""

    name = "citation_formatter"
    description = "Build a numbered citation list ([1], [2], ...) from analysis findings."

    def run(self, *, findings: list[AnalysisFinding]) -> list[Citation]:
        citations: list[Citation] = []
        seen: set[str] = set()
        for finding in findings:
            for evidence in finding.supporting_evidence:
                key = evidence.citation_key
                if key not in seen:
                    seen.add(key)
                    citations.append(
                        Citation(
                            marker=f"[{len(citations) + 1}]",
                            document=evidence.document,
                            page=evidence.page,
                        )
                    )
        return citations


class SourceFormatterTool(Tool):
    """Renders the citation list as a human-readable 'Sources' block."""

    name = "source_formatter"
    description = "Render citations as a readable list of sources."

    def run(self, *, citations: list[Citation]) -> list[str]:
        return [f"{c.marker} {c.document}, page/section {c.page}" for c in citations]


class ResponseFormatterTool(Tool):
    """Assembles the final markdown response from narrative text + optional tables."""

    name = "response_formatter"
    description = "Combine narrative text, tables and a sources block into one response."

    def run(
        self,
        *,
        body: str,
        sources: list[str],
        tables: list[ExtractedTable] | None = None,
        fmt: ResponseFormat = ResponseFormat.TEXT,
    ) -> str:
        if not body:
            raise ToolExecutionError("response_formatter requires a non-empty body")

        parts = [body.strip()]

        if fmt in (ResponseFormat.TABLE, ResponseFormat.MIXED) and tables:
            parts.extend(t.to_markdown() for t in tables)

        if sources:
            parts.append("**Sources**\n" + "\n".join(sources))

        return "\n\n".join(parts)
