"""
Answer Agent: turns the Analyst's findings + evidence into the final,
cited response shown to the user.
"""
from __future__ import annotations

from agents.base import Agent
from llm.client import LLMClient
from models.schemas import AnalysisResult, Citation, FinalAnswer, ResponseFormat
from tools.answer_tools import CitationFormatterTool, ResponseFormatterTool, SourceFormatterTool


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

    def run(self, *, analysis: AnalysisResult, fmt: ResponseFormat = ResponseFormat.TEXT) -> FinalAnswer:
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

        return FinalAnswer(text=text, format=fmt, citations=citations, sources=sources)

    def _write_body(self, analysis: AnalysisResult, marker_by_key: dict[str, str]) -> str:
        findings_block = "\n".join(
            f"- {f.statement} "
            + " ".join(marker_by_key.get(e.citation_key, "") for e in f.supporting_evidence)
            for f in analysis.findings
        )
        prompt = (
            f"Question: {analysis.question}\n\nFindings:\n{findings_block}\n\n"
            "Write a clear, well-organized answer for the user based only on "
            "these findings. Keep citation markers like [1] inline where relevant."
        )
        return self._llm.complete(prompt)
