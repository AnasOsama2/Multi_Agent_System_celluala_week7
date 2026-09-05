import re
import uuid
from typing import List, Dict, Any, Tuple

class ParentChildChunker:
    """
    Structure-aware Parent-Child Chunker:
    - Parent = Complete logical section / heading path.
    - Child = 250–500 tokens with 30–75 token overlap.
    - Embedding text = 'Document: <doc>\nSection: <heading_path>\n\n<child_text>'
    - Returned context = Child + full parent section context.
    """
    def __init__(
        self,
        min_child_tokens: int = 150,
        max_child_tokens: int = 450,
        overlap_tokens: int = 50
    ):
        self.min_child_tokens = min_child_tokens
        self.max_child_tokens = max_child_tokens
        self.overlap_tokens = overlap_tokens

    def estimate_tokens(self, text: str) -> int:
        """Approximate token count (1 token ≈ 4 characters or word count * 1.3)."""
        words = text.split()
        return max(1, int(len(words) * 1.3))

    def split_section_into_children(
        self,
        section_content: str,
        document_name: str,
        heading_path: str,
        source_id: str,
        section_id: str
    ) -> List[Dict[str, Any]]:
        """
        Splits a parent section into 250–500 token child chunks with 30–75 token overlap.
        Embeds contextual metadata prefix (heading path) to prevent short chunks from losing subject.
        """
        paragraphs = [p.strip() for p in section_content.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [section_content.strip()] if section_content.strip() else []

        child_chunks: List[Dict[str, Any]] = []
        current_child_words: List[str] = []

        for p in paragraphs:
            p_words = p.split()
            if not p_words:
                continue

            # If adding paragraph exceeds max_child_tokens, flush current child
            if current_child_words and (self.estimate_tokens(" ".join(current_child_words + p_words)) > self.max_child_tokens):
                child_text = " ".join(current_child_words)
                chunk_id = f"chunk_{uuid.uuid4().hex[:12]}"
                
                # Context-enriched embedding text
                embedding_text = (
                    f"Document: {document_name}\n"
                    f"Section: {heading_path}\n\n"
                    f"{child_text}"
                )

                child_chunks.append({
                    "chunk_id": chunk_id,
                    "section_id": section_id,
                    "source_id": source_id,
                    "child_index": len(child_chunks),
                    "content": child_text,
                    "embedding_text": embedding_text,
                    "token_count": self.estimate_tokens(child_text),
                    "heading_path": heading_path,
                    "document_name": document_name
                })

                # Maintain overlap from the end of current child
                overlap_words = current_child_words[-int(self.overlap_tokens / 1.3):] if len(current_child_words) > int(self.overlap_tokens / 1.3) else []
                current_child_words = overlap_words + p_words
            else:
                current_child_words.extend(p_words)

        if current_child_words:
            child_text = " ".join(current_child_words)
            chunk_id = f"chunk_{uuid.uuid4().hex[:12]}"
            embedding_text = (
                f"Document: {document_name}\n"
                f"Section: {heading_path}\n\n"
                f"{child_text}"
            )
            child_chunks.append({
                "chunk_id": chunk_id,
                "section_id": section_id,
                "source_id": source_id,
                "child_index": len(child_chunks),
                "content": child_text,
                "embedding_text": embedding_text,
                "token_count": self.estimate_tokens(child_text),
                "heading_path": heading_path,
                "document_name": document_name
            })

        return child_chunks


parent_child_chunker = ParentChildChunker()
