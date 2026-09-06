import uuid
import json
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.workflow.graph import rag_graph
from app.core.logging import app_logger

router = APIRouter(prefix="/api/v1", tags=["Query & Retrieval Agent"])

class QueryRequest(BaseModel):
    query: str = Field(..., examples=["What were total sales in Germany during March?"])
    filter_dict: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata filter dictionary")

class QueryResponse(BaseModel):
    query: str
    trace_id: str
    route: str
    route_reasoning: str
    is_high_confidence: bool
    confidence_score: float
    answer: str
    citations: List[Dict[str, Any]]
    sources: List[str] = Field(default_factory=list)
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    sufficiency: str = "ENOUGH"
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    iterations_used: int = 0
    sql_executed: Optional[str] = None
    sql_rows_count: int = 0
    feedback_passed: bool
    feedback_details: Dict[str, Any]

@router.post("/query", response_model=QueryResponse)
async def query_rag_agent(req: QueryRequest):
    """
    Execute full multi-agent Retrieval & Self-Correction graph on user query:
    1. Query Preprocessing & Router (SQL vs Hybrid vs Mixed).
    2. SQL Agent / Hybrid Retrieval.
    3. Retrieval Confidence Evaluation.
    4. Adaptive Reranking (BAAI/bge-reranker-v2-m3).
    5. Parent Context Expansion.
    6. Analyst Agent (sufficiency assessment, feedback loop, calculations, findings).
    7. Answer Agent (citation formatting, source rendering, final synthesis).
    8. Evaluator Feedback Loop & Self-Correction.
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    trace_id = f"trace_{uuid.uuid4().hex[:8]}"

    initial_state = {
        "query": req.query,
        "trace_id": trace_id,
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

    try:
        final_state = rag_graph.invoke(initial_state)

        sql_res = final_state.get("sql_result", {})
        return QueryResponse(
            query=req.query,
            trace_id=trace_id,
            route=final_state.get("route", "hybrid_search"),
            route_reasoning=final_state.get("route_reasoning", ""),
            is_high_confidence=final_state.get("is_high_confidence", False),
            confidence_score=final_state.get("confidence_score", 0.0),
            answer=final_state.get("answer", ""),
            citations=final_state.get("citations", []),
            sources=final_state.get("sources", []),
            findings=final_state.get("findings", []),
            sufficiency=final_state.get("sufficiency", "ENOUGH"),
            tables=final_state.get("tables", []),
            iterations_used=final_state.get("iterations_used", 0),
            sql_executed=sql_res.get("sql"),
            sql_rows_count=len(sql_res.get("rows", [])),
            feedback_passed=final_state.get("feedback_passed", True),
            feedback_details=final_state.get("feedback_details", {})
        )
    except Exception as e:
        app_logger.log_state(f"Graph execution failed: {str(e)}", step="api_query", level="error", trace_id=trace_id)
        raise HTTPException(status_code=500, detail=f"Retrieval Agent Error: {str(e)}")

@router.post("/query/stream")
async def query_rag_stream(req: QueryRequest):
    """
    Server-Sent Events (SSE) streaming endpoint that streams intermediate agent state transitions
    and final answer tokens.
    """
    trace_id = f"stream_{uuid.uuid4().hex[:8]}"

    async def event_generator():
        initial_state = {
            "query": req.query,
            "trace_id": trace_id,
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

        yield f"data: {json.dumps({'event': 'start', 'trace_id': trace_id})}\n\n"

        for output in rag_graph.stream(initial_state):
            for node_name, node_state in output.items():
                event_data = {
                    "event": "node_update",
                    "node": node_name,
                    "route": node_state.get("route"),
                    "confidence": node_state.get("confidence_score"),
                    "citations_count": len(node_state.get("citations", [])),
                    "feedback_passed": node_state.get("feedback_passed")
                }
                yield f"data: {json.dumps(event_data)}\n\n"

        # Final output
        final_state = rag_graph.invoke(initial_state)
        final_payload = {
            "event": "complete",
            "answer": final_state.get("answer"),
            "citations": final_state.get("citations"),
            "route": final_state.get("route")
        }
        yield f"data: {json.dumps(final_payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
