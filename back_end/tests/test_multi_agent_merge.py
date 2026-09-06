import pytest
from app.agents.schemas import EvidenceChunk, ResponseFormat
from app.agents.analyst_agent import AnalystAgent
from app.agents.answer_agent import AnswerAgent
from app.agents.analyst_tools import RetrieveMoreEvidenceTool
from app.agents.retriever_interface import RetrieverInterface
from app.agents.llm_adapter import LLMClient
from app.agents.retriever_adapter import PipelineRetrieverAdapter
from app.workflow.graph import rag_graph


class MockLLM(LLMClient):
    def complete(self, prompt: str, *, temperature: float = 0.2, max_tokens: int = 1500) -> str:
        if "Does this evidence contain the necessary" in prompt:
            return "ENOUGH"
        if "List the key findings" in prompt:
            return "- OAuth authentication uses client ID and secret [Source: doc.pdf, p.1]\n- Access tokens expire after 60 minutes"
        if "Write a clear, authoritative" in prompt:
            return "OAuth configuration requires a client ID and secret [1]. Access tokens expire in 60 minutes [2]."
        return "Standard mock LLM response"


class MockRetriever(RetrieverInterface):
    def retrieve(self, query: str, top_k: int = 5) -> list[EvidenceChunk]:
        return [
            EvidenceChunk("auth_guide.pdf", 1, "OAuth requires client ID and secret.", score=0.95),
            EvidenceChunk("auth_guide.pdf", 2, "Access tokens expire after 60 minutes.", score=0.88),
        ][:top_k]


def test_analyst_and_answer_agents_direct():
    llm = MockLLM()
    retriever_tool = RetrieveMoreEvidenceTool(MockRetriever())
    analyst = AnalystAgent(llm, retriever_tool, min_evidence_chunks=1)
    answerer = AnswerAgent(llm)

    initial_evidence = [
        EvidenceChunk("auth_guide.pdf", 1, "OAuth requires client ID and secret.", score=0.95)
    ]

    analysis = analyst.run(question="How is OAuth configured?", evidence=initial_evidence)
    assert analysis.sufficiency.name == "ENOUGH"
    assert len(analysis.findings) >= 1

    # Test calculator tool on analyst
    calc_res = analyst.use_tool("calculator", operation="add", values=[10.5, 20.5])
    assert calc_res == 31.0

    # Test answer agent
    final_ans = answerer.run(analysis=analysis, fmt=ResponseFormat.TEXT)
    assert len(final_ans.text) > 0
    assert len(final_ans.citations) >= 1
    assert len(final_ans.sources) >= 1


def test_retriever_adapter():
    adapter = PipelineRetrieverAdapter()
    chunks = adapter.retrieve("OAuth authentication client secret", top_k=2)
    assert isinstance(chunks, list)


def test_end_to_end_graph_multi_agent():
    state = {
        "query": "How do I configure OAuth in the application?",
        "trace_id": "test_multi_agent_merge",
        "route": "hybrid_search",
        "route_reasoning": "",
        "candidates": [],
        "is_high_confidence": False,
        "confidence_score": 0.0,
        "reranked_candidates": [],
        "top_candidates": [],
        "evidence_chunks": [],
        "sql_result": {},
        "context_text": "",
        "citations": [],
        "sources": [],
        "findings": [],
        "sufficiency": "ENOUGH",
        "tables": [],
        "iterations_used": 0,
        "answer": "",
        "feedback_passed": True,
        "feedback_details": {},
        "feedback_iteration": 0
    }

    res = rag_graph.invoke(state)
    assert "answer" in res
    assert len(res["answer"]) > 0
    assert "findings" in res
    assert "citations" in res
    assert "sources" in res
