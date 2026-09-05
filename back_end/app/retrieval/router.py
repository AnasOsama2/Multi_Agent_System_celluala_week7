import re
from typing import Dict, Any, Optional
from app.core.llm import llm_client
from app.core.logging import app_logger
from app.database.registry import registry

class QueryRouter:
    """
    Intelligent query router combining fast rule-based pattern matching
    with LLM classification for ambiguous intents.
    Routes queries to: 'sql', 'hybrid_search', or 'sql_and_hybrid'.
    """
    SQL_KEYWORDS = [
        r'\bhow many\b', r'\bcount\b', r'\bsum\b', r'\baverage\b', r'\bavg\b',
        r'\btotal\b', r'\bminimum\b', r'\bmin\b', r'\bmaximum\b', r'\bmax\b',
        r'\bbetween\s+\d{4}\b', r'\bwhich month\b', r'\bwhich year\b', r'\bgroup by\b',
        r'\bcompare values\b', r'\bsort by\b', r'\brank\b', r'\bgreater than\b',
        r'\bless than\b', r'\btop\s+\d+\b', r'\blowest\b', r'\bhighest\b',
        r'\brevenue\b', r'\bsales\b', r'\bprice\b', r'\bquantity\b'
    ]

    DOCUMENT_KEYWORDS = [
        r'\bexplain\b', r'\bwhat does this mean\b', r'\bhow do i\b', r'\bhow to\b',
        r'\bwhy does\b', r'\bfind documents\b', r'\bsummarize\b', r'\bwhat is the policy\b',
        r'\brequirements\b', r'\btroubleshoot\b', r'\bconfigure\b', r'\barchitecture\b',
        r'\bfunction\b', r'\bclass\b', r'\bmethod\b', r'\bcode\b'
    ]

    def route(self, query: str, trace_id: Optional[str] = None) -> Dict[str, Any]:
        query_lower = query.lower()

        has_datasets = len(registry.get_all_datasets()) > 0

        # Fast Rule-based classification
        sql_matches = sum(1 for p in self.SQL_KEYWORDS if re.search(p, query_lower))
        doc_matches = sum(1 for p in self.DOCUMENT_KEYWORDS if re.search(p, query_lower))

        if has_datasets:
            if sql_matches >= 1 and doc_matches >= 1:
                app_logger.log_routing(query, "sql_and_hybrid", f"Matched {sql_matches} SQL & {doc_matches} doc keywords", trace_id)
                return {"route": "sql_and_hybrid", "reasoning": "Query contains both numeric aggregation and conceptual context"}
            elif sql_matches >= 1 and doc_matches == 0:
                app_logger.log_routing(query, "sql", f"Matched {sql_matches} SQL keywords", trace_id)
                return {"route": "sql", "reasoning": "Query asks for aggregation, count, filter, or calculation"}

        # If purely documentary or no SQL tables exist
        if doc_matches >= 1 or not has_datasets:
            app_logger.log_routing(query, "hybrid_search", "Matched document keywords or no SQL datasets available", trace_id)
            return {"route": "hybrid_search", "reasoning": "Query asks for textual explanation or document search"}

        # LLM Classification for ambiguous queries
        return self._classify_with_llm(query, trace_id)

    def _classify_with_llm(self, query: str, trace_id: Optional[str]) -> Dict[str, Any]:
        catalog = registry.get_full_schema_catalog()
        
        prompt = f"""
You are a query classifier in a multi-modal RAG system.
Available Database Tables:
{catalog if catalog.strip() else "None"}

User Query: "{query}"

Determine the best retrieval route:
1. "sql": If the query can be answered purely by querying tabular data with calculations, counting, filtering, or aggregations.
2. "hybrid_search": If the query asks for explanations, documents, policies, code, or conceptual information.
3. "sql_and_hybrid": If the query requires finding records in a database AND retrieving textual policies/explanations.

Respond with strict JSON:
{{
  "route": "sql" | "hybrid_search" | "sql_and_hybrid",
  "reasoning": "short explanation"
}}
"""
        try:
            res = llm_client.generate_json(
                messages=[
                    {"role": "system", "content": "You are a precise query router. Output JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                trace_id=trace_id
            )
            route = res.get("route", "hybrid_search")
            reasoning = res.get("reasoning", "LLM router classification")
            app_logger.log_routing(query, route, reasoning, trace_id)
            return {"route": route, "reasoning": reasoning}
        except Exception as e:
            app_logger.log_routing(query, "hybrid_search", f"Fallback router ({e})", trace_id)
            return {"route": "hybrid_search", "reasoning": "Fallback default"}


query_router = QueryRouter()
