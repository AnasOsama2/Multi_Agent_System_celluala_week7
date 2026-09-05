import os
import re
import json
from typing import Any, Dict, List, Optional, Tuple
import chromadb
from chromadb.config import Settings as ChromaSettings
from rank_bm25 import BM25Okapi
from app.config import settings
from app.core.embeddings import embedding_client
from app.core.logging import app_logger

class HybridVectorStore:
    """
    Unified Vector + BM25 Keyword Store.
    Stores parent-child chunks, spreadsheet text columns, and extracted table descriptions.
    Supports cosine similarity, BM25 scoring, and formula-based hybrid weighting.
    """
    def __init__(self, persist_directory: Optional[str] = None):
        self.persist_directory = persist_directory or str(settings.chroma_dir)
        self.chroma_client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection = self.chroma_client.get_or_create_collection(
            name="document_chunks",
            metadata={"hnsw:space": "cosine"}
        )
        
        # BM25 in-memory index structures
        self._bm25_corpus: List[List[str]] = []
        self._bm25_doc_ids: List[str] = []
        self._bm25_metadata: List[Dict[str, Any]] = []
        self._bm25_index: Optional[BM25Okapi] = None
        self._rebuild_bm25()

    def _tokenize(self, text: str) -> List[str]:
        """Simple alphanumeric tokenizer for BM25."""
        return re.findall(r'\b\w+\b', text.lower())

    def _rebuild_bm25(self):
        """Builds BM25 index from current Chroma collection."""
        try:
            results = self.collection.get(include=["documents", "metadatas"])
            docs = results.get("documents", [])
            ids = results.get("ids", [])
            metas = results.get("metadatas", [])

            self._bm25_corpus = [self._tokenize(doc) for doc in docs]
            self._bm25_doc_ids = ids
            self._bm25_metadata = metas

            if self._bm25_corpus:
                self._bm25_index = BM25Okapi(self._bm25_corpus)
            else:
                self._bm25_index = None
        except Exception as e:
            app_logger.log_state(f"BM25 build error: {e}", step="vector_store", level="warning")

    def add_chunks(
        self,
        chunk_ids: List[str],
        embedding_texts: List[str],
        contents: List[str],
        metadatas: List[Dict[str, Any]],
        trace_id: Optional[str] = None
    ):
        """
        Embeds embedding_texts and adds them to ChromaDB and BM25 index.
        """
        if not chunk_ids:
            return

        embeddings = embedding_client.embed_documents(embedding_texts, trace_id=trace_id)
        
        # Ensure metadata values are strings, ints, floats, or bools for Chroma
        cleaned_metadatas = []
        for m in metadatas:
            clean_m = {}
            for k, v in m.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_m[k] = v
                elif v is None:
                    clean_m[k] = ""
                else:
                    clean_m[k] = json.dumps(v)
            cleaned_metadatas.append(clean_m)

        self.collection.upsert(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=cleaned_metadatas
        )

        # Update BM25
        self._rebuild_bm25()
        app_logger.log_state(
            event=f"Successfully indexed {len(chunk_ids)} chunks into Vector & BM25 store",
            step="vector_store",
            details={"chunk_count": len(chunk_ids)},
            trace_id=trace_id
        )

    def vector_search(
        self,
        query: str,
        top_k: int = 15,
        filter_dict: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Dense semantic search using BAAI/bge-m3 embeddings."""
        query_embedding = embedding_client.embed_query(query, trace_id=trace_id)
        
        where_filter = filter_dict if filter_dict else None
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, max(1, self.collection.count())),
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        candidates = []
        if results and results.get("ids") and len(results["ids"]) > 0:
            ids = results["ids"][0]
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            dists = results["distances"][0]

            for cid, doc, meta, dist in zip(ids, docs, metas, dists):
                # Cosine distance to similarity (Chroma returns cosine distance: 0 is identical, 2 is opposite)
                sim_score = max(0.0, 1.0 - (dist / 2.0))
                candidates.append({
                    "id": cid,
                    "content": doc,
                    "metadata": meta,
                    "semantic_score": sim_score,
                    "distance": dist
                })
        return candidates

    def keyword_search(
        self,
        query: str,
        top_k: int = 15
    ) -> List[Dict[str, Any]]:
        """Sparse keyword search using BM25Okapi."""
        if not self._bm25_index or not self._bm25_corpus:
            return []

        tokens = self._tokenize(query)
        if not tokens:
            return []

        scores = self._bm25_index.get_scores(tokens)
        max_score = max(scores) if max(scores) > 0 else 1.0

        scored_docs = []
        for i, score in enumerate(scores):
            if score > 0:
                normalized_score = score / max_score
                scored_docs.append({
                    "id": self._bm25_doc_ids[i],
                    "content": " ".join(self._bm25_corpus[i]),
                    "metadata": self._bm25_metadata[i] if i < len(self._bm25_metadata) else {},
                    "keyword_score": float(normalized_score),
                    "raw_bm25": float(score)
                })

        scored_docs.sort(key=lambda x: x["keyword_score"], reverse=True)
        return scored_docs[:top_k]

    def hybrid_search(
        self,
        query: str,
        top_k: int = 15,
        filter_dict: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining semantic search and BM25 using formula:
        hybrid_score = 0.5 * semantic_score + 0.3 * keyword_score + 0.1 * metadata_score + 0.1 * structural_score
        """
        vec_results = self.vector_search(query, top_k=top_k * 2, filter_dict=filter_dict, trace_id=trace_id)
        kw_results = self.keyword_search(query, top_k=top_k * 2)

        # Merge candidate pools by ID
        candidates_by_id: Dict[str, Dict[str, Any]] = {}

        for item in vec_results:
            cid = item["id"]
            candidates_by_id[cid] = {
                "id": cid,
                "content": item["content"],
                "metadata": item["metadata"],
                "semantic_score": item["semantic_score"],
                "keyword_score": 0.0,
                "metadata_score": 0.0,
                "structural_score": 0.0
            }

        for item in kw_results:
            cid = item["id"]
            if cid in candidates_by_id:
                candidates_by_id[cid]["keyword_score"] = item["keyword_score"]
            else:
                candidates_by_id[cid] = {
                    "id": cid,
                    "content": item.get("metadata", {}).get("content", item["content"]),
                    "metadata": item["metadata"],
                    "semantic_score": 0.0,
                    "keyword_score": item["keyword_score"],
                    "metadata_score": 0.0,
                    "structural_score": 0.0
                }

        # Calculate structural and metadata bonus
        query_lower = query.lower()
        w_sem = settings.weight_semantic
        w_kw = settings.weight_keyword
        w_meta = settings.weight_metadata
        w_struct = settings.weight_structural

        merged_list = []
        for cid, cand in candidates_by_id.items():
            meta = cand["metadata"]
            
            # Structural score: rewards heading match, document type match, class/function symbol match
            heading = str(meta.get("heading_path", "")).lower()
            symbol = str(meta.get("symbol_name", "")).lower()
            source_file = str(meta.get("source_file", "")).lower()

            struct_score = 0.0
            if any(term in heading for term in query_lower.split() if len(term) > 3):
                struct_score += 0.5
            if symbol and symbol in query_lower:
                struct_score += 0.5
            if any(term in source_file for term in query_lower.split() if len(term) > 3):
                struct_score += 0.3
            cand["structural_score"] = min(1.0, struct_score)

            # Metadata score: rewards filter criteria match or high provenance completeness
            meta_score = 0.5 if meta.get("section_id") or meta.get("table_name") else 0.0
            cand["metadata_score"] = meta_score

            # Hybrid score formula
            hybrid_score = (
                w_sem * cand["semantic_score"]
                + w_kw * cand["keyword_score"]
                + w_meta * cand["metadata_score"]
                + w_struct * cand["structural_score"]
            )
            cand["hybrid_score"] = float(hybrid_score)
            merged_list.append(cand)

        # Sort descending by hybrid_score
        merged_list.sort(key=lambda x: x["hybrid_score"], reverse=True)
        top_candidates = merged_list[:top_k]

        app_logger.log_retrieval(
            query=query,
            retrieved_count=len(top_candidates),
            top_scores=[c["hybrid_score"] for c in top_candidates],
            trace_id=trace_id
        )

        return top_candidates


vector_store = HybridVectorStore()
