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
        top_3 = candidates[:3]
    else:
        top_3 = []

    return {
        "is_high_confidence": is_high,
        "confidence_score": score,
        "top_candidates": top_3
    }

def rerank_node(state: RAGState) -> Dict[str, Any]:
    query = state["query"]
    candidates = state.get("candidates", [])
    trace_id = state.get("trace_id", "trace_default")
    
    top_3 = reranker_client.rerank(query, candidates, top_n=3, trace_id=trace_id)
    return {
        "reranked_candidates": top_3,
        "top_candidates": top_3
    }

def build_context_node(state: RAGState) -> Dict[str, Any]:
    top_candidates = state.get("top_candidates", [])
    expanded = parent_expander.expand(top_candidates)
    return {
        "context_text": expanded["context_text"],
        "citations": expanded["citations"]
    }

def generate_answer_node(state: RAGState) -> Dict[str, Any]:
    query = state["query"]
    route = state.get("route", "hybrid_search")
    context_text = state.get("context_text", "")
    sql_result = state.get("sql_result", {})
    citations = state.get("citations", [])
    trace_id = state.get("trace_id", "trace_default")

    system_prompt = """
You are an expert AI assistant providing high-precision answers strictly grounded in retrieved evidence.
Rules:
1. Base your answer strictly on the provided SQL database results and Document Reference context.
2. Do NOT hallucinate facts or extrapolate beyond the evidence.
3. If information is not found in the context, explicitly state what is missing.
4. Cite all sources using the format: [Source: <filename>, Section/Table: <details>].
"""

    user_content_parts = [f"User Question: {query}\n"]

    if sql_result and sql_result.get("success"):
        user_content_parts.append(
            f"### SQL Database Results:\n"
            f"Executed Query: `{sql_result.get('sql')}`\n"
            f"{sql_result.get('summary', '')}\n"
        )
    elif sql_result and sql_result.get("error"):
        user_content_parts.append(f"SQL Notice: {sql_result.get('error')}\n")

    if context_text.strip():
        user_content_parts.append(f"### Retrieved Document Context:\n{context_text}\n")

    user_content_parts.append("Provide a clear, comprehensive, and well-cited response:")

    full_prompt = "\n".join(user_content_parts)

    answer = llm_client.generate(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_prompt}
        ],
        temperature=0.1,
        trace_id=trace_id
    )

    return {"answer": answer}

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
    """
    Self-correction fallback node:
    Uses reformulated keywords to perform a BM25-boosted hybrid retrieval and reranks with BGE reranker.
    """
    eval_details = state.get("feedback_details", {})
    reformulated_query = eval_details.get("reformulation") or state["query"]
    trace_id = state.get("trace_id", "trace_default")

    app_logger.log_state(
        event=f"Executing self-correction fallback retrieval with query: '{reformulated_query}'",
        step="fallback_search",
        details={"original": state["query"], "reformulation": reformulated_query},
        trace_id=trace_id
    )

    # 1. Retrieve candidates with reformulated query
    candidates = hybrid_retriever.retrieve(reformulated_query, top_k=20, trace_id=trace_id)
    
    # 2. Rerank directly with BAAI/bge-reranker-v2-m3
    top_3 = reranker_client.rerank(reformulated_query, candidates, top_n=3, trace_id=trace_id)

    # 3. Expand parent context
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
    workflow.add_node("generate_answer", generate_answer_node)
    workflow.add_node("evaluate_feedback", evaluate_feedback_node)
    workflow.add_node("fallback_search", fallback_search_node)

    # Mixed handler node for parallel SQL + Retrieval
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

    workflow.add_edge("execute_sql", "generate_answer")
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
    workflow.add_edge("build_context", "generate_answer")
    workflow.add_edge("generate_answer", "evaluate_feedback")

    workflow.add_conditional_edges(
        "evaluate_feedback",
        feedback_decision,
        {
            END: END,
            "fallback_search": "fallback_search"
        }
    )

    # Fallback search feeds back into generation
    workflow.add_edge("fallback_search", "generate_answer")

    return workflow.compile()


rag_graph = create_rag_graph()
