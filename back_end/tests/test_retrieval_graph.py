import pytest
from app.retrieval.router import query_router
from app.retrieval.confidence import confidence_scorer
from app.core.reranker import reranker_client
from app.retrieval.feedback_evaluator import feedback_evaluator
from app.workflow.graph import rag_graph

def test_query_router_rules():
    # SQL routing
    res1 = query_router.route("What was the total revenue in March?")
    assert res1["route"] in ["sql", "sql_and_hybrid"]

    # Hybrid routing
    res2 = query_router.route("Explain how to configure OAuth authentication in the system")
    assert res2["route"] in ["hybrid_search", "sql_and_hybrid"]

def test_confidence_scorer():
    # High confidence candidate
    high_candidates = [
        {"content": "OAuth requires a client ID and secret.", "hybrid_score": 0.85},
        {"content": "Other details...", "hybrid_score": 0.40}
    ]
    is_high, score, action = confidence_scorer.evaluate(high_candidates)
    assert is_high
    assert action == "direct_top_3"

    # Low confidence candidate
    low_candidates = [
        {"content": "Vague snippet", "hybrid_score": 0.35},
        {"content": "Another snippet", "hybrid_score": 0.30}
    ]
    is_high_low, score_low, action_low = confidence_scorer.evaluate(low_candidates)
    assert not is_high_low
    assert action_low == "bge_reranker_top_3"

def test_reranker_scoring():
    query = "How to renew access tokens?"
    candidates = [
        {"content": "The weather today in Berlin is overcast.", "id": "1"},
        {"content": "To renew an access token, send a refresh_token request to /oauth/token.", "id": "2"},
        {"content": "Database backups occur daily at midnight.", "id": "3"}
    ]
    reranked = reranker_client.rerank(query, candidates, top_n=2)
    assert len(reranked) == 2
    # The relevant snippet should be ranked #1
    assert "renew an access token" in reranked[0]["content"]

def test_feedback_evaluator_pass():
    query = "What is the access token expiration time?"
    context = "Access tokens expire after 60 minutes."
    answer = "According to the documentation, access tokens expire after 60 minutes [Source: manual.md]."

    result = feedback_evaluator.evaluate(query, context, answer, iteration=1)
    assert result["passed"] is True

def test_end_to_end_graph_execution():
    state = {
        "query": "How does OAuth token renewal work?",
        "trace_id": "test_trace_1",
        "route": "hybrid_search",
        "route_reasoning": "",
        "candidates": [],
        "is_high_confidence": False,
        "confidence_score": 0.0,
        "reranked_candidates": [],
        "top_candidates": [],
        "sql_result": {},
        "context_text": "",
        "citations": [],
        "answer": "",
        "feedback_passed": True,
        "feedback_details": {},
        "feedback_iteration": 0
    }
    result = rag_graph.invoke(state)
    assert "answer" in result
    assert len(result["answer"]) > 0
