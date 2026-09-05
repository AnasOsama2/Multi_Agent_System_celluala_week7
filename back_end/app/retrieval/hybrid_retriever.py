import re
from typing import Dict, Any, List, Optional
from app.config import settings
from app.database.vector_store import vector_store
from app.core.logging import app_logger

class HybridRetriever:
    """
    Retrieves top candidate chunks using combined vector semantic similarity and BM25 keywords.
    """
    def preprocess_query(self, query: str) -> str:
        """Cleans and normalizes query text."""
        clean = re.sub(r'[\r\n\t]+', ' ', query)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_dict: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        k = top_k or settings.top_candidates_k
        clean_query = self.preprocess_query(query)

        candidates = vector_store.hybrid_search(
            query=clean_query,
            top_k=k,
            filter_dict=filter_dict,
            trace_id=trace_id
        )
        return candidates


hybrid_retriever = HybridRetriever()
