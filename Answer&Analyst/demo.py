"""
End-to-end demo of the Analyst Agent + Answer Agent working together,
using a scripted LLM and a mock Retriever so it runs with no API keys and
no network access. Swap DemoLLMClient for OpenAILLMClient /
AnthropicLLMClient (see llm/client.py) and MockRetriever for the real
Retriever Agent in production - nothing else in the agents changes.

Run with:  python demo.py
"""
from __future__ import annotations

from agents.analyst_agent import AnalystAgent
from agents.answer_agent import AnswerAgent
from agents.retriever_interface import RetrieverInterface
from llm.client import LLMClient
from models.schemas import EvidenceChunk, ResponseFormat
from tools.analyst_tools import (
    CalculatorTool,
    DataAnalysisTool,
    DocumentComparisonTool,
    RetrieveMoreEvidenceTool,
    TableExtractorTool,
)


class DemoLLMClient(LLMClient):
    """A tiny scripted LLM so the demo output is legible without an API key."""

    def complete(self, prompt: str, *, temperature: float = 0.2, max_tokens: int = 800) -> str:
        if "Does this evidence fully answer" in prompt:
            return "ENOUGH"
        if "List the key findings" in prompt:
            return (
                "- CNN accuracy across the three papers averages 92%\n"
                "- Paper B reports the highest single accuracy at 95%"
            )
        if "Write a clear, well-organized answer" in prompt:
            return (
                "Across the three papers, CNN accuracy averages 92%. "
                "Paper B reports the strongest single result at 95%, while "
                "Papers A and C report 92% and 89% respectively."
            )
        if "Compare the following documents" in prompt:
            return (
                "SIMILARITIES: all three papers evaluate a CNN on the same benchmark;\n"
                "DIFFERENCES: paper B uses a larger training set than A and C"
            )
        return "[unhandled prompt]"


class MockRetriever(RetrieverInterface):
    """Stands in for the real Retriever Agent (a teammate's task)."""

    def retrieve(self, query: str, top_k: int = 5) -> list[EvidenceChunk]:
        return [
            EvidenceChunk("paperC.pdf", 4, "CNN accuracy on the test set was 89%.", score=0.81)
        ][:top_k]


def main() -> None:
    llm = DemoLLMClient()
    retriever_tool = RetrieveMoreEvidenceTool(MockRetriever())

    analyst = AnalystAgent(llm, retriever_tool, min_evidence_chunks=3)
    answerer = AnswerAgent(llm)

    # --- Full workflow: Analyst assesses evidence, loops back to the
    # Retriever once because only 2 chunks came in, then Answer Agent
    # formats the cited final response. ---
    initial_evidence = [
        EvidenceChunk("paperA.pdf", 5, "CNN accuracy on the benchmark was 92%.", score=0.94),
        EvidenceChunk("paperB.pdf", 8, "The CNN model reached 95% accuracy.", score=0.91),
    ]

    analysis = analyst.run(
        question="What is the average CNN accuracy across the three papers?",
        evidence=initial_evidence,
    )
    print(f"Sufficiency: {analysis.sufficiency.name}  (feedback-loop iterations: {analysis.iterations_used})")
    for f in analysis.findings:
        print(" -", f.statement)

    answer = answerer.run(analysis=analysis, fmt=ResponseFormat.TEXT)
    print("\n--- FINAL ANSWER ---\n")
    print(answer.text)

    # --- Individual tool showcase (agent.use_tool is how the Analyst
    # calls each capability internally) ---
    print("\n--- TOOL SHOWCASE ---\n")

    avg = analyst.use_tool("calculator", operation="average", values=[92, 95, 89])
    print("calculator(average):", avg)

    table_chunk = EvidenceChunk("results.pdf", 2, "Model | Accuracy\nCNN | 92%\nRNN | 88%")
    table = analyst.use_tool("table_extractor", chunk=table_chunk)
    print("table_extractor:\n" + table.to_markdown())

    ranking = analyst.use_tool(
        "data_analysis", data={"paperA": 92.0, "paperB": 95.0, "paperC": 89.0}, mode="rank"
    )
    print("data_analysis(rank):", ranking)

    comparison = analyst.use_tool(
        "document_comparison",
        subject="CNN accuracy",
        chunks=initial_evidence + [EvidenceChunk("paperC.pdf", 4, "CNN accuracy was 89%.")],
    )
    print("document_comparison similarities:", comparison.similarities)
    print("document_comparison differences:", comparison.differences)


if __name__ == "__main__":
    main()
