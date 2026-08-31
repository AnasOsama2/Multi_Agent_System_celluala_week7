# Analyst Agent + Answer Agent

Implementation of the two agents assigned to you from the Project 3
multi-agent RAG pipeline (Retriever → **Analyst** → **Answer**), built as
a small, testable Python package rather than a script.

## Layout

```
agents/
  base.py                 Tool + Agent abstract base classes
  retriever_interface.py  the only thing Analyst needs from Retriever
  analyst_agent.py        AnalystAgent
  answer_agent.py         AnswerAgent
tools/
  analyst_tools.py        Calculator, TableExtractor, DocumentComparison,
                           DataAnalysis, RetrieveMoreEvidence
  answer_tools.py         CitationFormatter, SourceFormatter, ResponseFormatter
models/
  schemas.py               EvidenceChunk, AnalysisResult, FinalAnswer, ...
llm/
  client.py                LLMClient interface + Mock/OpenAI/Anthropic adapters
tests/                      pytest unit tests (13, all passing)
demo.py                     runnable end-to-end example, no API key needed
```

## Design

- **Tool / Agent (Strategy + Template Method)** — `agents/base.py` defines
  an abstract `Tool` (`name`, `description`, `run(**kwargs)`) and an
  abstract `Agent` that owns a registry of tools and exposes
  `use_tool(name, **kwargs)`. Both `AnalystAgent` and `AnswerAgent`
  subclass `Agent`; each new capability is a new `Tool` subclass, not a
  branch inside the agent — matches the diagram's "TOOLS" boxes 1:1.

- **LLMClient (Strategy)** — `llm/client.py` is an abstract interface with
  one method, `complete(prompt) -> str`. Neither agent imports an SDK
  directly, so you can hand them `OpenRouterLLMClient`, `OpenAILLMClient`,
  `AnthropicLLMClient`, a self-hosted adapter, or `MockLLMClient` for
  tests — no agent code changes. `OpenRouterLLMClient` reuses the
  `openai` SDK pointed at OpenRouter's base URL, since OpenRouter's API
  is OpenAI-compatible.

- **RetrieverInterface (Dependency Inversion)** — the Retriever Agent is a
  teammate's task, so the Analyst only depends on a one-method interface
  (`retrieve(query, top_k) -> list[EvidenceChunk]`). Wrap the real
  Retriever Agent in a class implementing this interface and pass it into
  `RetrieveMoreEvidenceTool`; the demo uses a `MockRetriever` stand-in.

- **Typed data contracts** — `models/schemas.py` holds frozen/plain
  dataclasses (`EvidenceChunk`, `AnalysisResult`, `FinalAnswer`, ...) so
  the Analyst → Answer handoff (and the eventual Retriever → Analyst
  handoff) is a typed object, not a dict with implicit keys.

- **Composition over duplication** — `DataAnalysisTool` reuses
  `CalculatorTool` internally instead of reimplementing averages/stdev.

- **Errors** — all tool failures surface as `ToolExecutionError`
  (`agents/base.py`), so an Orchestrator wrapping these agents only needs
  to catch one exception type.

## The feedback loop (Analyst ⇄ Retriever)

`AnalystAgent.run()` implements the diagram's decision node exactly:

1. `_assess_sufficiency()` — a cheap heuristic (`len(evidence) < min_evidence_chunks`)
   short-circuits the obvious case; otherwise the LLM is asked whether the
   evidence answers the question and, if not, what to search for next.
2. If insufficient and under `max_feedback_iterations`, it calls
   `use_tool("retrieve_more_evidence", query=follow_up)`, merges the new
   chunks (de-duplicated by `document, page`), and reassesses.
3. Once enough evidence is available (or the iteration cap is hit, so the
   loop can never hang forever), it builds grounded `AnalysisFinding`s and
   returns an `AnalysisResult` — this is what `AnswerAgent.run()` consumes.

## Running it

```bash
pip install -r requirements.txt   # only pytest, for the tests
python demo.py                    # end-to-end run with a scripted LLM
python -m pytest tests/ -v        # 13 unit tests
```

`demo.py` uses a tiny scripted `LLMClient` and a `MockRetriever` so it
runs with no API key and no network. To wire in real infrastructure:

```python
from llm.client import OpenRouterLLMClient
from agents.analyst_agent import AnalystAgent
from agents.answer_agent import AnswerAgent
from tools.analyst_tools import RetrieveMoreEvidenceTool

llm = OpenRouterLLMClient(api_key="...", model="openai/gpt-4o-mini")
retriever_tool = RetrieveMoreEvidenceTool(your_real_retriever_agent)  # implements RetrieverInterface

analyst = AnalystAgent(llm, retriever_tool, min_evidence_chunks=3, max_feedback_iterations=3)
answerer = AnswerAgent(llm)

analysis = analyst.run(question=q, evidence=evidence_from_retriever)
final = answerer.run(analysis=analysis)
print(final.text)
```

## Notes / next steps

- `DocumentComparisonTool` and the sufficiency/findings prompts currently
  parse the LLM's free-text reply with light string parsing. If your LLM
  provider supports structured/JSON output or tool-calling, swapping
  those prompts for a JSON schema would make parsing more robust — the
  `Tool` interface doesn't need to change.
- `TableExtractorTool` uses a heuristic (`|`-delimited or whitespace-aligned
  lines) since it works on the plain-text chunks the pipeline stores. If
  the Document Preparation Pipeline instead exposes native PDF table
  extraction (e.g. via `camelot` or `pdfplumber`), that library call can
  replace the body of `TableExtractorTool.run()` without touching the
  Analyst.
- `max_feedback_iterations` (default 3) exists precisely so the Analyst
  can never loop forever if the Retriever keeps returning the same/no
  evidence — tune it to taste.
