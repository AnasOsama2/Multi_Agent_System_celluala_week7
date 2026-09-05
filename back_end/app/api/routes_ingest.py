import shutil
import uuid
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.config import settings
from app.ingestion.pipeline import ingestion_pipeline
from app.database.registry import registry
from app.core.logging import app_logger

router = APIRouter(prefix="/api/v1", tags=["Ingestion"])

@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    owner_id: Optional[str] = Form("default_user")
):
    """
    Upload and ingest any supported document:
    - Unstructured Text (PDF, DOCX, Markdown, HTML, TXT)
    - Spreadsheets (CSV, Excel)
    - PDF with extractable tables
    - Structured data (JSON, XML)
    - Source code (Python, JS, TS, Go, Java, etc.)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")

    source_id = str(uuid.uuid4())
    trace_id = f"ingest_{source_id[:8]}"
    
    # Save uploaded file locally
    dest_path = settings.uploads_dir / f"{source_id}_{file.filename}"
    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        summary = ingestion_pipeline.ingest_file(
            file_path=dest_path,
            source_id=source_id,
            owner_id=owner_id or "default_user",
            trace_id=trace_id
        )
        return {
            "status": "success",
            "message": f"Successfully ingested {file.filename}",
            "data": summary
        }
    except Exception as e:
        app_logger.log_state(f"Ingestion failed: {str(e)}", step="api_ingest", level="error", trace_id=trace_id)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@router.get("/sources")
async def list_sources():
    """List all registered document sources in the system."""
    sources = registry.get_all_sources()
    return {"status": "success", "count": len(sources), "sources": sources}
