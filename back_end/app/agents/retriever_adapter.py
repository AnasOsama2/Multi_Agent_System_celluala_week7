"""
Retriever adapter that implements RetrieverInterface for AnalystAgent,
bridging hybrid retrieval, SQL execution, BGE-reranking, and parent context expansion.
"""
from __future__ import annotations

from typing import List, Dict, Any
from app.agents.retriever_interface import RetrieverInterface
from app.agents.schemas import EvidenceChunk
from app.retrieval.hybrid_retriever import hybrid_retriever
from app.retrieval.confidence import confidence_scorer
from app.core.reranker import reranker_client
from app.retrieval.parent_expander import parent_expander
from app.retrieval.sql_agent import sql_agent
from app.retrieval.router import query_router
from app.core.logging import app_logger


class PipelineRetrieverAdapter(RetrieverInterface):
    """
    Implements RetrieverInterface by routing and querying the multimodal
    ChromaDB + BM25 + SQLite storage engines.
    """

    def __init__(self, trace_id: str | None = None) -> None:
        self.trace_id = trace_id

    def retrieve(self, query: str, top_k: int = 5) -> list[EvidenceChunk]:
        trace_id = self.trace_id or "adapter_retrieval"
        app_logger.log_state(
            event=f"PipelineRetrieverAdapter: retrieving top {top_k} evidence chunks for query: '{query}'",
            step="retriever_adapter",
            details={"query": query, "top_k": top_k},
            trace_id=trace_id
        )

        evidence_chunks: list[EvidenceChunk] = []

        # 1. Route query to see if SQL is relevant
        routing = query_router.route(query, trace_id=trace_id)
        route = routing.get("route", "hybrid_search")

        # If SQL or mixed route, execute SQL first
        if route in ("sql", "sql_and_hybrid"):
            sql_res = sql_agent.execute_query(query, trace_id=trace_id)
            if sql_res.get("success") and sql_res.get("rows"):
                summary_table = sql_res.get("summary", "")
                sql_chunk = EvidenceChunk(
                    document=f"SQL Database ({sql_res.get('columns', [])})",
                    page=1,
                    content=f"Query: {sql_res.get('sql')}\nResults:\n{summary_table}",
                    score=1.0,
                    metadata={"is_sql": True, "rows": sql_res.get("rows")}
                )
                evidence_chunks.append(sql_chunk)

        # 2. If hybrid search or mixed, run hybrid retrieval
        if route in ("hybrid_search", "sql_and_hybrid") or not evidence_chunks:
            candidates = hybrid_retriever.retrieve(query, top_k=max(10, top_k * 2), trace_id=trace_id)
            if candidates:
                # Evaluate confidence
                is_high, score, action = confidence_scorer.evaluate(candidates, trace_id=trace_id)
                if is_high:
                    selected = candidates[:top_k]
                else:
                    selected = reranker_client.rerank(query, candidates, top_n=top_k, trace_id=trace_id)

                # Expand to parent context
                for item in selected:
                    meta = item.get("metadata", {})
                    doc_name = meta.get("source_file") or meta.get("document_name") or "Document"
                    page_num = meta.get("page_number") or meta.get("child_index", 1) or 1
                    
                    # Get expanded content or raw chunk content
                    expanded = parent_expander.expand([item])
                    content = expanded.get("context_text") or item.get("content", "")

                    evidence_chunks.append(
                        EvidenceChunk(
                            document=str(doc_name),
                            page=int(page_num) if isinstance(page_num, int) or (isinstance(page_num, str) and page_num.isdigit()) else 1,
                            content=content,
                            score=float(item.get("rerank_score", item.get("hybrid_score", 0.8))),
                            metadata=meta
                        )
                    )

        return evidence_chunks[:top_k]
