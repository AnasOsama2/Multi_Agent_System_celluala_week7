import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "documentation" in data

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "models" in data

def test_ingest_and_query_flow(tmp_path):
    # Create sample markdown
    sample_content = b"""# API Documentation

## Rate Limits
The API enforces a limit of 100 requests per minute for standard users.
Premium users receive 1000 requests per minute with burst capability.
"""
    # Upload via /api/v1/ingest
    files = {"file": ("api_docs.md", sample_content, "text/markdown")}
    ingest_res = client.post("/api/v1/ingest", files=files, data={"owner_id": "test_suite"})
    assert ingest_res.status_code == 200
    ingest_data = ingest_res.json()
    assert ingest_data["status"] == "success"

    # Query via /api/v1/query
    query_payload = {"query": "What is the rate limit for standard users?"}
    query_res = client.post("/api/v1/query", json=query_payload)
    assert query_res.status_code == 200
    query_data = query_res.json()
    assert "answer" in query_data
    assert len(query_data["answer"]) > 0
    assert "100" in query_data["answer"]

def test_metadata_endpoints():
    res = client.get("/api/v1/datasets")
    assert res.status_code == 200
    assert "datasets" in res.json()

    res_schema = client.get("/api/v1/schemas")
    assert res_schema.status_code == 200
    assert "catalog" in res_schema.json()
