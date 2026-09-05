import os
import time
from typing import List, Union
import numpy as np
from huggingface_hub import InferenceClient
from app.config import settings
from app.core.logging import app_logger

class EmbeddingClient:
    """
    Embedding client utilizing BAAI/bge-m3 via Hugging Face API
    with batching, dimension validation, and local sentence-transformers fallback.
    """
    def __init__(self):
        self._hf_client = None
        self._local_model = None

    @property
    def hf_client(self) -> InferenceClient:
        if self._hf_client is None:
            token = settings.effective_hf_token
            if not token:
                raise ValueError("Hugging Face token is missing. Set HF_token in .env")
            self._hf_client = InferenceClient(token=token)
        return self._hf_client

    def embed_documents(self, texts: List[str], trace_id: str = None) -> List[List[float]]:
        if not texts:
            return []

        embeddings: List[List[float]] = []
        batch_size = 16

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                # Feature extraction via HF InferenceClient
                res = self.hf_client.feature_extraction(
                    batch,
                    model=settings.embedding_model
                )
                
                # Format numpy / list response
                if isinstance(res, np.ndarray):
                    # If 3D (batch, seq_len, dim), mean pool
                    if res.ndim == 3:
                        res = np.mean(res, axis=1)
                    batch_embs = res.tolist()
                elif isinstance(res, list):
                    # Check if nested sequence of tokens or list of embeddings
                    if len(res) > 0 and isinstance(res[0], list):
                        if len(res[0]) > 0 and isinstance(res[0][0], list):
                            # (batch, seq, dim)
                            arr = np.mean(np.array(res), axis=1)
                            batch_embs = arr.tolist()
                        else:
                            batch_embs = res
                    else:
                        batch_embs = [res]
                else:
                    raise ValueError(f"Unexpected embedding output format: {type(res)}")
                
                embeddings.extend(batch_embs)
            except Exception as e:
                app_logger.log_state(
                    event=f"HF Inference embedding failed ({str(e)}), attempting local fallback...",
                    step="embeddings",
                    level="warning",
                    trace_id=trace_id
                )
                # Fallback to local sentence-transformers
                fallback_embs = self._embed_local(batch)
                embeddings.extend(fallback_embs)

        return embeddings

    def embed_query(self, text: str, trace_id: str = None) -> List[float]:
        res = self.embed_documents([text], trace_id=trace_id)
        if res:
            return res[0]
        return [0.0] * 1024

    def _embed_local(self, texts: List[str]) -> List[List[float]]:
        if self._local_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._local_model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception as e:
                app_logger.log_state(
                    event=f"Local embedding fallback model load failed: {str(e)}",
                    step="embeddings",
                    level="error"
                )
                # Dummy embedding
                return [[0.0] * 384 for _ in texts]
        
        embs = self._local_model.encode(texts, convert_to_numpy=True)
        return embs.tolist()


embedding_client = EmbeddingClient()
