from agents.analyst_agent import AnalystAgent
from agents.answer_agent import AnswerAgent
from agents.retriever_interface import RetrieverInterface
from llm.client import LLMClient
from models.schemas import EvidenceChunk, EvidenceSufficiency, ResponseFormat
from tools.analyst_tools import RetrieveMoreEvidenceTool


class ScriptedLLM(LLMClient):
    """Routes canned answers by sniffing which prompt was sent."""

    def complete(self, prompt: str, *, temperature: float = 0.2, max_tokens: int = 800) -> str:
        if "Does this evidence fully answer" in prompt:
            return "ENOUGH"
        if "List the key findings" in prompt:
            return "- CNN accuracy averages 92%"
        if "Write a clear, well-organized answer" in prompt:
            return "The average CNN accuracy is 92%."
        return ""


class StubRetriever(RetrieverInterface):
    def __init__(self, chunks: list[EvidenceChunk]) -> None:
        self._chunks = chunks

    def retrieve(self, query: str, top_k: int = 5) -> list[EvidenceChunk]:
        return self._chunks[:top_k]


def test_analyst_skips_feedback_loop_when_evidence_already_enough():
    llm = ScriptedLLM()
    retriever_tool = RetrieveMoreEvidenceTool(StubRetriever([]))
    analyst = AnalystAgent(llm, retriever_tool, min_evidence_chunks=1)

    evidence = [EvidenceChunk("paperA.pdf", 5, "CNN accuracy was 92%.")]
    result = analyst.run(question="What is the CNN accuracy?", evidence=evidence)

    assert result.sufficiency is EvidenceSufficiency.ENOUGH
    assert result.iterations_used == 0
    assert len(result.findings) == 1


def test_analyst_triggers_feedback_loop_when_evidence_too_thin():
    llm = ScriptedLLM()
    extra_chunk = EvidenceChunk("paperC.pdf", 4, "CNN accuracy was 89%.")
    retriever_tool = RetrieveMoreEvidenceTool(StubRetriever([extra_chunk]))
    # min_evidence_chunks=2 forces the heuristic to reject a single chunk
    analyst = AnalystAgent(llm, retriever_tool, min_evidence_chunks=2)

    evidence = [EvidenceChunk("paperA.pdf", 5, "CNN accuracy was 92%.")]
    result = analyst.run(question="What is the CNN accuracy?", evidence=evidence)

    assert result.iterations_used == 1
    assert result.sufficiency is EvidenceSufficiency.ENOUGH


def test_analyst_stops_after_max_iterations_even_if_still_insufficient():
    class NeverEnoughLLM(LLMClient):
        def complete(self, prompt: str, *, temperature: float = 0.2, max_tokens: int = 800) -> str:
            if "Does this evidence fully answer" in prompt:
                return "INSUFFICIENT: need more data"
            return "- some finding"

    retriever_tool = RetrieveMoreEvidenceTool(StubRetriever([]))  # never returns anything new
    analyst = AnalystAgent(NeverEnoughLLM(), retriever_tool, min_evidence_chunks=1, max_feedback_iterations=2)

    evidence = [EvidenceChunk("paperA.pdf", 5, "some content")]
    result = analyst.run(question="Q?", evidence=evidence)

    assert result.iterations_used == 2
    assert result.sufficiency is EvidenceSufficiency.INSUFFICIENT


def test_answer_agent_produces_cited_text_and_sources():
    llm = ScriptedLLM()
    retriever_tool = RetrieveMoreEvidenceTool(StubRetriever([]))
    analyst = AnalystAgent(llm, retriever_tool, min_evidence_chunks=1)
    answerer = AnswerAgent(llm)

    evidence = [EvidenceChunk("paperA.pdf", 5, "CNN accuracy was 92%.")]
    analysis = analyst.run(question="What is the CNN accuracy?", evidence=evidence)
    answer = answerer.run(analysis=analysis, fmt=ResponseFormat.TEXT)

    assert "The average CNN accuracy is 92%." in answer.text
    assert answer.sources == ["[1] paperA.pdf, page 5"]
    assert "**Sources**" in answer.text
