from typing import List, Dict, Any, Tuple
from app.config import settings
from app.core.logging import app_logger

class RetrievalConfidenceScorer:
    """
    Evaluates the quality of retrieved candidates.
    If high confidence (strong top score and clear separation), picks Top 3 directly.
    If low confidence, routes candidates to BAAI/bge-reranker-v2-m3.
    """
    def __init__(self, threshold: float = None):
        self.threshold = threshold or settings.confidence_threshold

    def evaluate(
        self,
        candidates: List[Dict[str, Any]],
        trace_id: str = None
    ) -> Tuple[bool, float, str]:
        if not candidates:
            app_logger.log_confidence(0.0, False, "No candidates found", trace_id)
            return False, 0.0, "no_candidates"

        top_cand = candidates[0]
        top_score = top_cand.get("hybrid_score", top_cand.get("semantic_score", 0.0))

        # Check score margin if multiple candidates
        margin = 0.0
        if len(candidates) >= 3:
            cand3_score = candidates[2].get("hybrid_score", candidates[2].get("semantic_score", 0.0))
            margin = top_score - cand3_score

        is_high = top_score >= self.threshold

        action = "direct_top_3" if is_high else "bge_reranker_top_3"
        app_logger.log_confidence(top_score, is_high, action, trace_id)

        return is_high, float(top_score), action


confidence_scorer = RetrievalConfidenceScorer()
