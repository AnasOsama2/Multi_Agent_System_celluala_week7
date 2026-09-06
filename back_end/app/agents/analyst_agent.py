"""
Analyst Agent: evaluates evidence sufficiency, extracts tables,
runs calculations/statistics, compares documents, and drives the feedback loop
back to the Retriever Agent.
"""
from __future__ import annotations

from app.agents.base import Agent
from app.agents.llm_adapter import LLMClient
from app.agents.schemas import (
    AnalysisFinding,
    AnalysisResult,
    EvidenceChunk,
    EvidenceSufficiency,
)
from app.agents.analyst_tools import (
    CalculatorTool,
    DataAnalysisTool,
    DocumentComparisonTool,
    RetrieveMoreEvidenceTool,
    TableExtractorTool,
)
from app.core.logging import app_logger


class AnalystAgent(Agent):
    """
    Owns: Calculator, Table Extractor, Document Comparison, Data Analysis,
    and Retrieve-More-Evidence. Implements the ANALYSIS -> EVIDENCE
    ASSESSMENT -> (enough evidence? yes/no) loop.
    """

    def __init__(
        self,
        llm: LLMClient,
        retriever_tool: RetrieveMoreEvidenceTool,
        *,
        min_evidence_chunks: int = 1,
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

    def run(self, *, question: str, evidence: list[EvidenceChunk], trace_id: str | None = None) -> AnalysisResult:
        pool = list(evidence)
        iterations = 0
        sufficiency = EvidenceSufficiency.INSUFFICIENT
        follow_up: str | None = None

        app_logger.log_state(
            event=f"AnalystAgent starting evaluation for question: '{question}' with {len(evidence)} initial evidence chunks",
            step="analyst_agent",
            details={"question": question, "initial_evidence_count": len(evidence)},
            trace_id=trace_id
        )

        while True:
            sufficiency, follow_up = self._assess_sufficiency(question, pool)
            if sufficiency is EvidenceSufficiency.ENOUGH or iterations >= self._max_feedback_iterations:
                break

            app_logger.log_state(
                event=f"AnalystAgent: Evidence insufficient on iteration {iterations+1}, requesting more evidence: '{follow_up}'",
                step="analyst_agent_feedback",
                details={"iteration": iterations + 1, "follow_up_query": follow_up},
                trace_id=trace_id
            )
            new_chunks = self.use_tool("retrieve_more_evidence", query=follow_up, top_k=5)
            pool = _merge_evidence(pool, new_chunks)
            iterations += 1

        # Check for extractable tables
        extracted_tables = []
        for chunk in pool:
            if "|" in chunk.content or "\t" in chunk.content:
                try:
                    table = self.use_tool("table_extractor", chunk=chunk)
                    if len(table.rows) > 1 and len(table.headers) > 1:
                        extracted_tables.append(table)
                except Exception:
                    pass

        findings = self._build_findings(question, pool)

        app_logger.log_state(
            event=f"AnalystAgent completed analysis with {len(findings)} findings (Sufficiency: {sufficiency.name}, Iterations: {iterations})",
            step="analyst_agent",
            details={
                "findings_count": len(findings),
                "sufficiency": sufficiency.name,
                "iterations_used": iterations,
                "tables_count": len(extracted_tables)
            },
            trace_id=trace_id
        )

        return AnalysisResult(
            question=question,
            findings=findings,
            sufficiency=sufficiency,
            tables=extracted_tables,
            follow_up_query=follow_up if sufficiency is EvidenceSufficiency.INSUFFICIENT else None,
            iterations_used=iterations,
        )

    def _assess_sufficiency(
        self, question: str, evidence: list[EvidenceChunk]
    ) -> tuple[EvidenceSufficiency, str | None]:
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
        if not evidence:
            return [AnalysisFinding(statement="No relevant evidence was found in the indexed sources.", supporting_evidence=[])]

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
        "Does this evidence contain the necessary factual information to answer the question? "
        "Reply 'ENOUGH' if yes, or 'INSUFFICIENT: <specific keywords or sub-query to retrieve>' if no."
    )


def _findings_prompt(question: str, evidence: list[EvidenceChunk]) -> str:
    ev_block = "\n".join(f"- ({e.citation_key}) {e.content}" for e in evidence)
    return (
        f"Question: {question}\n\nEvidence:\n{ev_block}\n\n"
        "List the key findings that answer the question, one per line, "
        "grounded only in the evidence above."
    )
