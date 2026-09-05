import mimetypes
from pathlib import Path
from typing import Dict, Any

class DocumentDetector:
    """
    Detects file types and classifies them into appropriate ingestion storage routes.
    """
    EXT_MAP = {
        # Unstructured documents
        ".pdf": "pdf",
        ".docx": "docx",
        ".doc": "docx",
        ".md": "markdown",
        ".markdown": "markdown",
        ".html": "html",
        ".htm": "html",
        ".txt": "text",
        ".rst": "text",
        
        # Spreadsheets / Tabular
        ".csv": "csv",
        ".tsv": "csv",
        ".xlsx": "excel",
        ".xls": "excel",
        
        # Structured Data
        ".json": "json",
        ".xml": "xml",
        
        # Code symbols
        ".py": "code",
        ".js": "code",
        ".ts": "code",
        ".jsx": "code",
        ".tsx": "code",
        ".java": "code",
        ".go": "code",
        ".rs": "code",
        ".cpp": "code",
        ".c": "code",
        ".sql": "code",
        ".sh": "code",
    }

    @classmethod
    def detect(cls, file_path: Path) -> Dict[str, Any]:
        suffix = file_path.suffix.lower()
        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"

        doc_category = cls.EXT_MAP.get(suffix, "unknown")
        
        if doc_category in ["pdf", "docx", "markdown", "html", "text"]:
            storage_route = "unstructured_document"
        elif doc_category in ["csv", "excel"]:
            storage_route = "spreadsheet"
        elif doc_category in ["json", "xml"]:
            storage_route = "structured_data"
        elif doc_category == "code":
            storage_route = "source_code"
        else:
            storage_route = "unstructured_document"

        return {
            "filename": file_path.name,
            "extension": suffix,
            "mime_type": mime_type,
            "category": doc_category,
            "storage_route": storage_route,
            "size_bytes": file_path.stat().st_size if file_path.exists() else 0
        }


detector = DocumentDetector()
