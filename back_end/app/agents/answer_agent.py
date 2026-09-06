"""
Answer Agent: synthesizes the Analyst's findings and evidence into the final,
cited response with inline markers ([1], [2]) and structured sources.
"""
from __future__ import annotations

from app.agents.base import Agent
from app.agents.llm_adapter import LLMClient
from app.agents.schemas import AnalysisResult, Citation, FinalAnswer, ResponseFormat
from app.agents.answer_tools import CitationFormatterTool, ResponseFormatterTool, SourceFormatterTool
from app.core.logging import app_logger


class AnswerAgent(Agent):
    """Owns: Citation Formatter, Source Formatter, Response Formatter."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm
        super().__init__(
            tools=[
                CitationFormatterTool(),
                SourceFormatterTool(),
                ResponseFormatterTool(),
            ]
        )

    def run(
        self,
        *,
        analysis: AnalysisResult,
        fmt: ResponseFormat = ResponseFormat.TEXT,
        trace_id: str | None = None
    ) -> FinalAnswer:
        app_logger.log_state(
            event=f"AnswerAgent composing final cited response from {len(analysis.findings)} findings",
            step="answer_agent",
            details={"findings_count": len(analysis.findings), "format": fmt.name},
            trace_id=trace_id
        )

        citations: list[Citation] = self.use_tool("citation_formatter", findings=analysis.findings)
        sources = self.use_tool("source_formatter", citations=citations)
        marker_by_key = {f"{c.document}, p.{c.page}": c.marker for c in citations}

        cited_body = self._write_body(analysis, marker_by_key)

        text = self.use_tool(
            "response_formatter",
            body=cited_body,
            sources=sources,
            tables=analysis.tables,
            fmt=fmt,
        )

        app_logger.log_state(
            event="AnswerAgent generated final response successfully",
            step="answer_agent",
            details={"citations_count": len(citations), "body_length": len(text)},
            trace_id=trace_id
        )

        return FinalAnswer(text=text, format=fmt, citations=citations, sources=sources)

    def _write_body(self, analysis: AnalysisResult, marker_by_key: dict[str, str]) -> str:
        findings_block = "\n".join(
            f"- {f.statement} "
            + " ".join(marker_by_key.get(e.citation_key, "") for e in f.supporting_evidence)
            for f in analysis.findings
        )
        prompt = (
            f"Question: {analysis.question}\n\nFindings:\n{findings_block}\n\n"
            "Write a clear, authoritative, and well-organized answer for the user based strictly on "
            "these findings. Retain inline citation markers like [1], [2] where appropriate. "
            "Do not fabricate any information."
        )
        return self._llm.complete(prompt)
