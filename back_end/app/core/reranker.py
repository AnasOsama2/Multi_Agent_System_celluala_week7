import os
import time
from typing import List, Dict, Any, Tuple
from huggingface_hub import InferenceClient
from app.config import settings
from app.core.logging import app_logger

class RerankerClient:
    """
    Reranker client using BAAI/bge-reranker-v2-m3 via Hugging Face API
    with local CrossEncoder fallback.
    """
    def __init__(self):
        self._hf_client = None
        self._local_reranker = None

    @property
    def hf_client(self) -> InferenceClient:
        if self._hf_client is None:
            token = settings.effective_hf_token
            if not token:
                raise ValueError("Hugging Face token is missing. Set HF_token in .env")
            self._hf_client = InferenceClient(token=token)
        return self._hf_client

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_n: int = 3,
        trace_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank a list of candidate chunk dictionaries.
        Each candidate is expected to have 'text' or 'page_content' or 'content' in candidate dict.
        """
        if not candidates:
            return []
        
        if len(candidates) <= top_n and len(candidates) == 1:
            return candidates

        texts_to_score: List[str] = []
        for c in candidates:
            chunk_text = c.get("text") or c.get("page_content") or c.get("content") or ""
            # Format query-passage pair
            texts_to_score.append(chunk_text)

        scores: List[float] = []
        try:
            # Score each pair using HF Inference text_classification
            for candidate_text in texts_to_score:
                # BGE reranker format text
                pair_input = f"{query}\n{candidate_text}"
                res = self.hf_client.text_classification(
                    model=settings.reranker_model,
                    text=pair_input
                )
                
                # Extract score
                if res and len(res) > 0:
                    score = res[0].score if hasattr(res[0], "score") else 0.5
                else:
                    score = 0.5
                scores.append(score)
        except Exception as e:
            app_logger.log_state(
                event=f"HF Reranker API error ({str(e)}), attempting local scoring...",
                step="reranker",
                level="warning",
                trace_id=trace_id
            )
            scores = self._score_local(query, texts_to_score)

        # Attach scores to candidates and sort
        scored_candidates = []
        for cand, score in zip(candidates, scores):
            updated_cand = dict(cand)
            updated_cand["rerank_score"] = float(score)
            scored_candidates.append(updated_cand)

        # Sort descending by rerank_score
        scored_candidates.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        top_reranked = scored_candidates[:top_n]

        app_logger.log_rerank(
            reranked_count=len(candidates),
            top_scores=[c.get("rerank_score", 0.0) for c in top_reranked],
            trace_id=trace_id
        )

        return top_reranked

    def _score_local(self, query: str, texts: List[str]) -> List[float]:
        if self._local_reranker is None:
            try:
                from sentence_transformers import CrossEncoder
                self._local_reranker = CrossEncoder("BAAI/bge-reranker-v2-m3")
            except Exception:
                try:
                    from sentence_transformers import CrossEncoder
                    self._local_reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
                except Exception as e:
                    app_logger.log_state(
                        event=f"Local CrossEncoder fallback failed: {str(e)}",
                        step="reranker",
                        level="error"
                    )
                    # Length/lexical heuristic fallback
                    return [0.5 for _ in texts]
        
        pairs = [[query, txt] for txt in texts]
        scores = self._local_reranker.predict(pairs)
        return [float(s) for s in scores]


reranker_client = RerankerClient()
