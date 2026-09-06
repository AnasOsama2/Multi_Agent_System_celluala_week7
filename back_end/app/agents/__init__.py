"""
Analyst Agent and Answer Agent integration module.
Exposes AnalystAgent, AnswerAgent, tools, schemas, and adapters.
"""
from app.agents.schemas import (
    EvidenceChunk,
    EvidenceSufficiency,
    AnalysisFinding,
    AnalysisResult,
    ExtractedTable,
    ComparisonResult,
    Citation,
    FinalAnswer,
    ResponseFormat
)
from app.agents.base import Tool, Agent, ToolExecutionError
from app.agents.retriever_interface import RetrieverInterface
from app.agents.analyst_agent import AnalystAgent
from app.agents.answer_agent import AnswerAgent
from app.agents.analyst_tools import (
    CalculatorTool,
    TableExtractorTool,
    DocumentComparisonTool,
    DataAnalysisTool,
    RetrieveMoreEvidenceTool
)
from app.agents.answer_tools import (
    CitationFormatterTool,
    SourceFormatterTool,
    ResponseFormatterTool
)
from app.agents.llm_adapter import GroqLLMClientAdapter
from app.agents.retriever_adapter import PipelineRetrieverAdapter

__all__ = [
    "EvidenceChunk",
    "EvidenceSufficiency",
    "AnalysisFinding",
    "AnalysisResult",
    "ExtractedTable",
    "ComparisonResult",
    "Citation",
    "FinalAnswer",
    "ResponseFormat",
    "Tool",
    "Agent",
    "ToolExecutionError",
    "RetrieverInterface",
    "AnalystAgent",
    "AnswerAgent",
    "CalculatorTool",
    "TableExtractorTool",
    "DocumentComparisonTool",
    "DataAnalysisTool",
    "RetrieveMoreEvidenceTool",
    "CitationFormatterTool",
    "SourceFormatterTool",
    "ResponseFormatterTool",
    "GroqLLMClientAdapter",
    "PipelineRetrieverAdapter"
]
