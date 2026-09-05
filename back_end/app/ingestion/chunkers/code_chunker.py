import uuid
from typing import List, Dict, Any

class CodeChunker:
    """
    Transforms code symbols into vector & BM25 indexable chunks with structured embedding headers.
    """
    def chunk_symbols(
        self,
        symbols: List[Dict[str, Any]],
        source_id: str,
        document_name: str
    ) -> List[Dict[str, Any]]:
        chunks: List[Dict[str, Any]] = []

        for idx, sym in enumerate(symbols):
            chunk_id = f"code_{uuid.uuid4().hex[:12]}"
            
            # Structured header for semantic embeddings
            header_lines = [
                f"Repository: {sym.get('repository', 'repo')}",
                f"File: {sym.get('file_path', document_name)}",
                f"Language: {sym.get('language', 'text')}",
                f"Symbol: {sym.get('symbol_name', '')} ({sym.get('symbol_type', '')})",
                f"Signature: {sym.get('signature', '')}",
            ]
            if sym.get("imports"):
                header_lines.append(f"Imports: {sym['imports']}")
            if sym.get("docstring"):
                header_lines.append(f"Docstring: {sym['docstring']}")

            header = "\n".join(header_lines)
            code_body = sym.get("code", "")
            
            embedding_text = f"{header}\n\nCode:\n{code_body}"
            
            chunks.append({
                "chunk_id": chunk_id,
                "source_id": source_id,
                "symbol_id": f"{source_id}_sym_{idx}",
                "content": code_body,
                "embedding_text": embedding_text,
                "metadata": {
                    "source_id": source_id,
                    "source_file": document_name,
                    "symbol_name": sym.get("symbol_name", ""),
                    "symbol_type": sym.get("symbol_type", ""),
                    "language": sym.get("language", ""),
                    "signature": sym.get("signature", ""),
                    "line_start": sym.get("line_start", 1),
                    "line_end": sym.get("line_end", 1)
                }
            })

        return chunks


code_chunker = CodeChunker()
