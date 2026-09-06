from typing import TypedDict, List, Dict, Any, Optional

class RAGState(TypedDict):
    query: str
    trace_id: str
    
    # Routing
    route: str  # 'sql', 'hybrid_search', 'sql_and_hybrid'
    route_reasoning: str
    
    # Document Candidates & Evidence
    candidates: List[Dict[str, Any]]
    is_high_confidence: bool
    confidence_score: float
    reranked_candidates: List[Dict[str, Any]]
    top_candidates: List[Dict[str, Any]]
    evidence_chunks: List[Dict[str, Any]]
    
    # SQL Execution
    sql_result: Dict[str, Any]
    
    # Context & Citations
    context_text: str
    citations: List[Dict[str, Any]]
    sources: List[str]
    
    # Analyst Agent Outputs
    findings: List[Dict[str, Any]]
    sufficiency: str
    tables: List[Dict[str, Any]]
    iterations_used: int
    
    # Answer Agent Generation & Feedback Evaluation
    answer: str
    feedback_passed: bool
    feedback_details: Dict[str, Any]
    feedback_iteration: int
