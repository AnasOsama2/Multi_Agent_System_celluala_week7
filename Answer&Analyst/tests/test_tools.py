import pytest

from agents.base import ToolExecutionError
from llm.client import LLMClient
from models.schemas import AnalysisFinding, EvidenceChunk
from tools.analyst_tools import CalculatorTool, DataAnalysisTool, TableExtractorTool
from tools.answer_tools import CitationFormatterTool, SourceFormatterTool


class ScriptedLLM(LLMClient):
    def __init__(self, reply: str) -> None:
        self._reply = reply

    def complete(self, prompt: str, *, temperature: float = 0.2, max_tokens: int = 800) -> str:
        return self._reply


def test_calculator_average():
    assert CalculatorTool().run(operation="average", values=[92, 95, 89]) == pytest.approx(92.0)


def test_calculator_rejects_unknown_operation():
    with pytest.raises(ToolExecutionError):
        CalculatorTool().run(operation="frobnicate", values=[1])


def test_calculator_rejects_empty_values():
    with pytest.raises(ToolExecutionError):
        CalculatorTool().run(operation="average", values=[])


def test_table_extractor_pipe_delimited():
    chunk = EvidenceChunk("paper.pdf", 3, "Model | Accuracy\nCNN | 92%\nRNN | 88%")
    table = TableExtractorTool().run(chunk=chunk)
    assert table.headers == ["Model", "Accuracy"]
    assert table.rows == [["CNN", "92%"], ["RNN", "88%"]]


def test_table_extractor_falls_back_for_plain_text():
    chunk = EvidenceChunk("paper.pdf", 3, "just a plain sentence")
    table = TableExtractorTool().run(chunk=chunk)
    assert table.headers == ["content"]


def test_data_analysis_rank():
    result = DataAnalysisTool().run(data={"A": 92, "B": 95, "C": 89}, mode="rank")
    assert result[0] == ("B", 95)


def test_data_analysis_summary():
    result = DataAnalysisTool().run(data={"A": 92, "B": 95, "C": 89}, mode="summary")
    assert result["average"] == pytest.approx(92.0)
    assert result["max"] == 95


def test_citation_formatter_dedupes_and_numbers():
    ev1 = EvidenceChunk("paperA.pdf", 5, "text")
    ev2 = EvidenceChunk("paperB.pdf", 8, "text")
    findings = [
        AnalysisFinding("finding 1", [ev1, ev2]),
        AnalysisFinding("finding 2", [ev1]),  # ev1 repeated -> should not duplicate
    ]
    citations = CitationFormatterTool().run(findings=findings)
    assert [c.marker for c in citations] == ["[1]", "[2]"]
    assert (citations[0].document, citations[0].page) == ("paperA.pdf", 5)


def test_source_formatter_renders_readable_lines():
    ev1 = EvidenceChunk("paperA.pdf", 5, "text")
    citations = CitationFormatterTool().run(findings=[AnalysisFinding("f", [ev1])])
    lines = SourceFormatterTool().run(citations=citations)
    assert lines == ["[1] paperA.pdf, page 5"]
