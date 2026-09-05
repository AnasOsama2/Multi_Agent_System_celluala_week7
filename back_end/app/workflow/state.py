from typing import TypedDict, List, Dict, Any, Optional

class RAGState(TypedDict):
    query: str
    trace_id: str
    
    # Routing
    route: str  # 'sql', 'hybrid_search', 'sql_and_hybrid'
    route_reasoning: str
    
    # Document Candidates
    candidates: List[Dict[str, Any]]
    is_high_confidence: bool
    confidence_score: float
    reranked_candidates: List[Dict[str, Any]]
    top_candidates: List[Dict[str, Any]]
    
    # SQL Execution
    sql_result: Dict[str, Any]
    
    # Context & Citations
    context_text: str
    citations: List[Dict[str, Any]]
    
    # Generation & Evaluation
    answer: str
    feedback_passed: bool
    feedback_details: Dict[str, Any]
    feedback_iteration: int
