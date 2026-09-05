# Multi-Agent Multimodal Document Loading Pipeline & LangGraph Retrieval Agent

Production-grade Document Loading Pipeline and Retrieval Agent with:
- **LangGraph** workflow orchestration & state machine.
- **Groq LLM**: `qwen/qwen3.8-27b` for routing, SQL generation, synthesis, and feedback evaluation.
- **Hugging Face Reranker**: `BAAI/bge-reranker-v2-m3` with adaptive confidence routing.
- **Dense Embeddings**: `BAAI/bge-m3` via Hugging Face Inference API.
- **Hybrid Storage & Indexing**:
  - **SQLite**: Dynamic relational tables, dataset catalog (`dataset_metadata`), and column catalog (`column_metadata`).
  - **ChromaDB**: Dense semantic vector store for parent-child chunks and spreadsheet text columns.
  - **rank-bm25**: Sparse keyword index for exact match search.
- **Evaluator Feedback Loop**: Detects exact-match or semantic failures and automatically self-corrects via BM25-boosted merge & rerank.
- **FastAPI**: Clean RESTful API with structured logging and streaming endpoints.

---

## System Architecture

### 1. Ingestion Pipeline Routing Formula
- **Unstructured Documents (PDF, DOCX, Markdown, HTML, TXT)**: Split into logical sections (parents) and 250–500 token children with 30–75 token overlap and rich heading path headers (`Document: ... \n Section: ... \n ...`).
- **Spreadsheets (CSV, Excel)**: Inferred data types, normalized SQL table names (`doc_{id}_{sheet}`), indexed B-Tree columns, LLM-generated dataset & column catalogs, and long text columns indexed in vector store with SQL `row_id` link.
- **PDF with Tables**: Extracted into 3 representations: Original Markdown table, Relational SQL table, and Search Description for semantic discovery.
- **JSON / XML**: Object hierarchy mapped to SQL tables or document records.
- **Source Code (Python, JS, TS, etc.)**: Symbol-level chunking (Repository, File, Language, Class, Method, Signature, Imports, Docstring, Code).

### 2. Retrieval Agent & Feedback Loop
```
                      USER QUERY
                          │
                          ▼
                 Query Preprocessing
                          │
                          ▼
            Query Router (Rules + LLM)
             ┌────────────┼────────────┐
             ▼            ▼            ▼
            SQL         Hybrid       Mixed
          Branch        Search      Branch
             │            │            │
             │            ▼            │
             │     Top 10-20 Chunks    │
             │            │            │
             │    Confidence Check     │
             │     ┌──────┴──────┐     │
             │     ▼             ▼     │
             │   Top 3      BGE-Reranker
             │     │          (Top 3)  │
             │     └──────┬──────┘     │
             │            ▼            │
             │     Context Builder     │
             │    (Parent Expansion)   │
             │            │            │
             └────────────┬────────────┘
                          ▼
              Answer Generation (Groq Qwen 3.8 27B)
                          │
                          ▼
               Evaluator Feedback Loop
                 ┌────────┴────────┐
                 ▼                 ▼
             Pass (Fidelity)    Fail (Exact-Match Gap)
                 │                 │
                 ▼                 ▼
            Final Output     Fallback Search:
                          (BM25 Boost + Merge + Rerank)
```

---

## Quick Start

### 1. Requirements
Ensure your `.env` in project root contains:
```env
groq_key="your_groq_api_key"
HF_token="your_hugging_face_token"
```

### 2. Start the FastAPI Server
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser for the Swagger UI.

### 3. Ingest a Document
```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -F "file=@sample_document.pdf" \
  -F "owner_id=admin"
```

### 4. Query the Agent
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What were total sales in Germany during March?"}'
```

### 5. Inspect Datasets & Schemas
- List Datasets: `GET /api/v1/datasets`
- View Schema Catalog: `GET /api/v1/schemas`
- View Table Columns & Sample Rows: `GET /api/v1/tables/{table_name}`
- System Health: `GET /api/v1/health`

---

## Running the Automated Test Suite
```bash
pytest back_end/tests -vv
```
All 16 tests verify ingestion across document formats, SQL validation, LangGraph routing, BGE reranker scoring, feedback self-correction, and API endpoints.
