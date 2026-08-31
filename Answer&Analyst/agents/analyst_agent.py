"""
Analyst Agent: evaluates evidence, extracts tables, compares documents,
runs numeric analysis, and drives the feedback loop back to the Retriever
Agent until the Evidence Assessment step is satisfied.
"""
from __future__ import annotations

from agents.base import Agent
from llm.client import LLMClient
from models.schemas import (
    AnalysisFinding,
    AnalysisResult,
    EvidenceChunk,
    EvidenceSufficiency,
)
from tools.analyst_tools import (
    CalculatorTool,
    DataAnalysisTool,
    DocumentComparisonTool,
    RetrieveMoreEvidenceTool,
    TableExtractorTool,
)


class AnalystAgent(Agent):
    """
    Owns: Calculator, Table Extractor, Document Comparison, Data Analysis,
    and Retrieve-More-Evidence. Implements the ANALYSIS -> EVIDENCE
    ASSESSMENT -> (enough evidence? yes/no) loop from the workflow diagram.
    """

    def __init__(
        self,
        llm: LLMClient,
        retriever_tool: RetrieveMoreEvidenceTool,
        *,
        min_evidence_chunks: int = 2,
        max_feedback_iterations: int = 3,
    ) -> None:
        self._llm = llm
        self._min_evidence_chunks = min_evidence_chunks
        self._max_feedback_iterations = max_feedback_iterations

        super().__init__(
            tools=[
                CalculatorTool(),
                TableExtractorTool(),
                DocumentComparisonTool(llm),
                DataAnalysisTool(),
                retriever_tool,
            ]
        )

    def run(self, *, question: str, evidence: list[EvidenceChunk]) -> AnalysisResult:
        pool = list(evidence)
        iterations = 0
        sufficiency = EvidenceSufficiency.INSUFFICIENT
        follow_up: str | None = None

        while True:
            sufficiency, follow_up = self._assess_sufficiency(question, pool)
            if sufficiency is EvidenceSufficiency.ENOUGH or iterations >= self._max_feedback_iterations:
                break

            self._logger.info("Evidence insufficient, requesting more: %r", follow_up)
            new_chunks = self.use_tool("retrieve_more_evidence", query=follow_up, top_k=5)
            pool = _merge_evidence(pool, new_chunks)
            iterations += 1

        findings = self._build_findings(question, pool)

        return AnalysisResult(
            question=question,
            findings=findings,
            sufficiency=sufficiency,
            follow_up_query=follow_up if sufficiency is EvidenceSufficiency.INSUFFICIENT else None,
            iterations_used=iterations,
        )

    def _assess_sufficiency(
        self, question: str, evidence: list[EvidenceChunk]
    ) -> tuple[EvidenceSufficiency, str | None]:
        """
        The 'Evidence Assessment' decision node. A cheap heuristic (do we
        even have enough distinct chunks?) short-circuits the obvious
        case; otherwise the LLM judges whether the evidence answers the
        question and, if not, proposes the follow-up query for the
        Retriever.
        """
        if len(evidence) < self._min_evidence_chunks:
            return EvidenceSufficiency.INSUFFICIENT, question

        verdict = self._llm.complete(_sufficiency_prompt(question, evidence)).strip()

        if verdict.upper().startswith("ENOUGH"):
            return EvidenceSufficiency.ENOUGH, None
        follow_up = verdict.split(":", 1)[1].strip() if ":" in verdict else question
        return EvidenceSufficiency.INSUFFICIENT, follow_up

    def _build_findings(
        self, question: str, evidence: list[EvidenceChunk]
    ) -> list[AnalysisFinding]:
        raw = self._llm.complete(_findings_prompt(question, evidence))
        statements = [s.strip("- ").strip() for s in raw.splitlines() if s.strip()]
        if not statements:
            statements = [raw.strip()]

        return [
            AnalysisFinding(statement=statement, supporting_evidence=evidence)
            for statement in statements
        ]


def _merge_evidence(
    existing: list[EvidenceChunk], new: list[EvidenceChunk]
) -> list[EvidenceChunk]:
    seen = {e.citation_key for e in existing}
    merged = list(existing)
    for chunk in new:
        if chunk.citation_key not in seen:
            merged.append(chunk)
            seen.add(chunk.citation_key)
    return merged


def _sufficiency_prompt(question: str, evidence: list[EvidenceChunk]) -> str:
    ev_block = "\n".join(f"- ({e.citation_key}) {e.content}" for e in evidence)
    return (
        f"Question: {question}\n\nEvidence:\n{ev_block}\n\n"
        "Does this evidence fully answer the question? "
        "Reply 'ENOUGH' if yes, or 'INSUFFICIENT: <a more specific follow-up query>' if no."
    )


def _findings_prompt(question: str, evidence: list[EvidenceChunk]) -> str:
    ev_block = "\n".join(f"- ({e.citation_key}) {e.content}" for e in evidence)
    return (
        f"Question: {question}\n\nEvidence:\n{ev_block}\n\n"
        "List the key findings that answer the question, one per line, "
        "grounded only in the evidence above."
    )
