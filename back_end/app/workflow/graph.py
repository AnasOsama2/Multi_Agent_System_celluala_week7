import uuid
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from app.workflow.state import RAGState
from app.retrieval.router import query_router
from app.retrieval.sql_agent import sql_agent
from app.retrieval.hybrid_retriever import hybrid_retriever
from app.retrieval.confidence import confidence_scorer
from app.core.reranker import reranker_client
from app.retrieval.parent_expander import parent_expander
from app.retrieval.feedback_evaluator import feedback_evaluator
from app.core.llm import llm_client
from app.core.logging import app_logger

# Import Analyst and Answer Agents
from app.agents.schemas import EvidenceChunk, AnalysisFinding, AnalysisResult, EvidenceSufficiency, ResponseFormat
from app.agents.analyst_agent import AnalystAgent
from app.agents.answer_agent import AnswerAgent
from app.agents.analyst_tools import RetrieveMoreEvidenceTool
from app.agents.retriever_adapter import PipelineRetrieverAdapter
from app.agents.llm_adapter import GroqLLMClientAdapter

# ----------------- NODE DEFINITIONS ----------------- #

def route_query_node(state: RAGState) -> Dict[str, Any]:
    query = state["query"]
    trace_id = state.get("trace_id", "trace_default")
    route_res = query_router.route(query, trace_id=trace_id)
    return {
        "route": route_res["route"],
        "route_reasoning": route_res["reasoning"]
    }

def execute_sql_node(state: RAGState) -> Dict[str, Any]:
    query = state["query"]
    trace_id = state.get("trace_id", "trace_default")
    sql_res = sql_agent.execute_query(query, trace_id=trace_id)
    return {"sql_result": sql_res}

def hybrid_retrieval_node(state: RAGState) -> Dict[str, Any]:
    query = state["query"]
    trace_id = state.get("trace_id", "trace_default")
    candidates = hybrid_retriever.retrieve(query, trace_id=trace_id)
    return {"candidates": candidates}

def evaluate_confidence_node(state: RAGState) -> Dict[str, Any]:
    candidates = state.get("candidates", [])
    trace_id = state.get("trace_id", "trace_default")
    is_high, score, action = confidence_scorer.evaluate(candidates, trace_id=trace_id)
    
    if is_high:
        top_candidates = candidates[:6]
    else:
        top_candidates = []

    return {
        "is_high_confidence": is_high,
        "confidence_score": score,
        "top_candidates": top_candidates
    }

def rerank_node(state: RAGState) -> Dict[str, Any]:
    query = state["query"]
    candidates = state.get("candidates", [])
    trace_id = state.get("trace_id", "trace_default")
    
    top_candidates = reranker_client.rerank(query, candidates, top_n=6, trace_id=trace_id)
    return {
        "reranked_candidates": top_candidates,
        "top_candidates": top_candidates
    }

def build_context_node(state: RAGState) -> Dict[str, Any]:
    top_candidates = state.get("top_candidates", [])
    expanded = parent_expander.expand(top_candidates)
    return {
        "context_text": expanded["context_text"],
        "citations": expanded["citations"]
    }

def analyst_node(state: RAGState) -> Dict[str, Any]:
    """
    Analyst Agent node: evaluates evidence sufficiency, extracts tables,
    computes analysis, and constructs atomic findings.
    """
    query = state["query"]
    trace_id = state.get("trace_id", "trace_default")
    top_candidates = state.get("top_candidates", [])
    sql_result = state.get("sql_result", {})

    evidence_chunks: List[EvidenceChunk] = []

    # If SQL result exists, convert to EvidenceChunk
    if sql_result and sql_result.get("success") and sql_result.get("rows"):
        summary_table = sql_result.get("summary", "")
        evidence_chunks.append(
            EvidenceChunk(
                document=f"SQL Database ({sql_result.get('columns', [])})",
                page=1,
                content=f"Executed Query: {sql_result.get('sql')}\nResults:\n{summary_table}",
                score=1.0,
                metadata={"is_sql": True, "rows": sql_result.get("rows")}
            )
        )

    # Convert document candidates to EvidenceChunk using parent section content
    from app.database.registry import registry
    for c in top_candidates:
        meta = c.get("metadata", {})
        doc_name = meta.get("source_file") or meta.get("document_name") or "Document"
        page_val = meta.get("page_number") or meta.get("child_index", 1) or 1
        page_num = int(page_val) if str(page_val).isdigit() else 1
        
        # Use full parent section content if available to avoid passing partial/TOC fragments
        sec_id = meta.get("section_id")
        parent_sec = registry.get_section(sec_id) if sec_id else None
        chunk_content = parent_sec.get("content") if (parent_sec and parent_sec.get("content")) else c.get("content", "")
        
        evidence_chunks.append(
            EvidenceChunk(
                document=str(doc_name),
                page=page_num,
                content=chunk_content,
                score=float(c.get("rerank_score", c.get("hybrid_score", 0.8))),
                metadata=meta
            )
        )

    # Instantiate AnalystAgent with Groq LLM and Retriever adapter
    llm_adapter = GroqLLMClientAdapter()
    retriever_adapter = PipelineRetrieverAdapter(trace_id=trace_id)
    retriever_tool = RetrieveMoreEvidenceTool(retriever_adapter)
    analyst_agent = AnalystAgent(llm_adapter, retriever_tool, min_evidence_chunks=1, max_feedback_iterations=2)

    # Run analysis
    analysis: AnalysisResult = analyst_agent.run(question=query, evidence=evidence_chunks, trace_id=trace_id)

    findings_dicts = [
        {
            "statement": f.statement,
            "supporting_evidence": [e.citation_key for e in f.supporting_evidence],
            "computed_value": f.computed_value
        }
        for f in analysis.findings
    ]

    tables_dicts = [
        {"headers": t.headers, "rows": t.rows, "markdown": t.to_markdown()}
        for t in analysis.tables
    ]

    return {
        "findings": findings_dicts,
        "sufficiency": analysis.sufficiency.name,
        "tables": tables_dicts,
        "iterations_used": analysis.iterations_used,
        "evidence_chunks": [
            {"document": e.document, "page": e.page, "content": e.content, "score": e.score}
            for e in evidence_chunks
        ]
    }

def answer_node(state: RAGState) -> Dict[str, Any]:
    """
    Answer Agent node: transforms findings into cited response with inline markers and source list.
    """
    query = state["query"]
    trace_id = state.get("trace_id", "trace_default")
    findings_dicts = state.get("findings", [])
    tables_dicts = state.get("tables", [])
    evidence_dicts = state.get("evidence_chunks", [])

    # Reconstruct objects for AnswerAgent
    evidence_map = {}
    for ed in evidence_dicts:
        ec = EvidenceChunk(
            document=ed["document"],
            page=ed["page"],
            content=ed["content"],
            score=ed.get("score", 0.0)
        )
        evidence_map[ec.citation_key] = ec

    findings = []
    for fd in findings_dicts:
        sup_evidence = [evidence_map[k] for k in fd.get("supporting_evidence", []) if k in evidence_map]
        if not sup_evidence:
            sup_evidence = list(evidence_map.values())[:2]
        findings.append(
            AnalysisFinding(
                statement=fd["statement"],
                supporting_evidence=sup_evidence,
                computed_value=fd.get("computed_value")
            )
        )

    from app.agents.schemas import ExtractedTable
    tables = []
    for td in tables_dicts:
        dummy_chunk = list(evidence_map.values())[0] if evidence_map else EvidenceChunk("Document", 1, "")
        tables.append(ExtractedTable(source=dummy_chunk, headers=td["headers"], rows=td["rows"]))

    analysis_res = AnalysisResult(
        question=query,
        findings=findings,
        sufficiency=EvidenceSufficiency[state.get("sufficiency", "ENOUGH")],
        tables=tables,
        iterations_used=state.get("iterations_used", 0)
    )

    llm_adapter = GroqLLMClientAdapter()
    answer_agent = AnswerAgent(llm_adapter)
    fmt = ResponseFormat.MIXED if tables else ResponseFormat.TEXT
    final_answer = answer_agent.run(analysis=analysis_res, fmt=fmt, trace_id=trace_id)

    citations_list = [
        {"marker": c.marker, "document": c.document, "page": c.page}
        for c in final_answer.citations
    ]

    return {
        "answer": final_answer.text,
        "citations": citations_list,
        "sources": final_answer.sources
    }

def evaluate_feedback_node(state: RAGState) -> Dict[str, Any]:
    query = state["query"]
    context = state.get("context_text", "")
    answer = state.get("answer", "")
    iteration = state.get("feedback_iteration", 0) + 1
    trace_id = state.get("trace_id", "trace_default")

    eval_result = feedback_evaluator.evaluate(
        query=query,
        context=context,
        answer=answer,
        iteration=iteration,
        trace_id=trace_id
    )

    return {
        "feedback_passed": eval_result["passed"],
        "feedback_details": eval_result,
        "feedback_iteration": iteration
    }

def fallback_search_node(state: RAGState) -> Dict[str, Any]:
    eval_details = state.get("feedback_details", {})
    reformulated_query = eval_details.get("reformulation") or state["query"]
    trace_id = state.get("trace_id", "trace_default")

    app_logger.log_state(
        event=f"Executing self-correction fallback retrieval with query: '{reformulated_query}'",
        step="fallback_search",
        details={"original": state["query"], "reformulation": reformulated_query},
        trace_id=trace_id
    )

    candidates = hybrid_retriever.retrieve(reformulated_query, top_k=20, trace_id=trace_id)
    top_3 = reranker_client.rerank(reformulated_query, candidates, top_n=3, trace_id=trace_id)
    expanded = parent_expander.expand(top_3)

    return {
        "candidates": candidates,
        "reranked_candidates": top_3,
        "top_candidates": top_3,
        "context_text": expanded["context_text"],
        "citations": expanded["citations"]
    }

# ----------------- CONDITIONAL ROUTING ----------------- #

def route_decision(state: RAGState) -> str:
    route = state.get("route", "hybrid_search")
    if route == "sql":
        return "execute_sql"
    elif route == "sql_and_hybrid":
        return "mixed_branch"
    else:
        return "hybrid_retrieval"

def confidence_decision(state: RAGState) -> str:
    if state.get("is_high_confidence"):
        return "build_context"
    return "rerank"

def feedback_decision(state: RAGState) -> str:
    if state.get("feedback_passed") or state.get("feedback_iteration", 1) >= 2:
        return END
    return "fallback_search"

# ----------------- GRAPH COMPILATION ----------------- #

def create_rag_graph():
    workflow = StateGraph(RAGState)

    # Add Nodes
    workflow.add_node("route_query", route_query_node)
    workflow.add_node("execute_sql", execute_sql_node)
    workflow.add_node("hybrid_retrieval", hybrid_retrieval_node)
    workflow.add_node("evaluate_confidence", evaluate_confidence_node)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("build_context", build_context_node)
    workflow.add_node("analyst_agent", analyst_node)
    workflow.add_node("answer_agent", answer_node)
    workflow.add_node("evaluate_feedback", evaluate_feedback_node)
    workflow.add_node("fallback_search", fallback_search_node)

    # Mixed handler node
    def mixed_node(state: RAGState) -> Dict[str, Any]:
        sql_part = execute_sql_node(state)
        retrieval_part = hybrid_retrieval_node(state)
        return {**sql_part, **retrieval_part}
    
    workflow.add_node("mixed_branch", mixed_node)

    # Graph Edges
    workflow.set_entry_point("route_query")

    workflow.add_conditional_edges(
        "route_query",
        route_decision,
        {
            "execute_sql": "execute_sql",
            "hybrid_retrieval": "hybrid_retrieval",
            "mixed_branch": "mixed_branch"
        }
    )

    workflow.add_edge("execute_sql", "analyst_agent")
    workflow.add_edge("hybrid_retrieval", "evaluate_confidence")
    workflow.add_edge("mixed_branch", "evaluate_confidence")

    workflow.add_conditional_edges(
        "evaluate_confidence",
        confidence_decision,
        {
            "build_context": "build_context",
            "rerank": "rerank"
        }
    )

    workflow.add_edge("rerank", "build_context")
    workflow.add_edge("build_context", "analyst_agent")
    workflow.add_edge("analyst_agent", "answer_agent")
    workflow.add_edge("answer_agent", "evaluate_feedback")

    workflow.add_conditional_edges(
        "evaluate_feedback",
        feedback_decision,
        {
            END: END,
            "fallback_search": "fallback_search"
        }
    )

    workflow.add_edge("fallback_search", "analyst_agent")

    return workflow.compile()


rag_graph = create_rag_graph()
