import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.core.logging import app_logger
from app.database.registry import registry
from app.api.routes_ingest import router as ingest_router
from app.api.routes_query import router as query_router
from app.api.routes_metadata import router as metadata_router
from app.api.routes_health import router as health_router

app = FastAPI(
    title="Multi-Agent Multimodal RAG & Document Ingestion System",
    description="Production-grade Document Loading Pipeline and LangGraph Retrieval Agent with BAAI/bge-reranker-v2-m3 and Qwen 3.8 27B from Groq",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Timing & Correlation ID Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-ID", f"req_{uuid.uuid4().hex[:8]}")
    start_time = time.time()
    
    app_logger.log_state(
        event=f"Incoming {request.method} {request.url.path}",
        step="http_request",
        trace_id=trace_id
    )

    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        
        app_logger.log_state(
            event=f"Completed {request.method} {request.url.path} -> {response.status_code} ({duration_ms:.2f}ms)",
            step="http_response",
            trace_id=trace_id
        )
        return response
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        app_logger.log_state(
            event=f"Unhandled exception on {request.method} {request.url.path}: {str(e)}",
            step="http_error",
            level="error",
            trace_id=trace_id
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "error": str(e), "trace_id": trace_id}
        )

# Register Routers
app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(query_router)
app.include_router(metadata_router)

# Mount React Frontend assets if built
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
assets_dir = os.path.join(frontend_dist, "assets")
if os.path.isdir(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.get("/")
async def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept and os.path.isdir(frontend_dist):
        index_file = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
    return {
        "message": "Multi-Agent RAG & Document Pipeline API is running",
        "documentation": "/docs",
        "endpoints": {
            "health": "/api/v1/health",
            "ingest": "/api/v1/ingest",
            "query": "/api/v1/query",
            "datasets": "/api/v1/datasets",
            "schemas": "/api/v1/schemas"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
