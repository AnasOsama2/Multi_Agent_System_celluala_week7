from fastapi import APIRouter, HTTPException
from app.database.registry import registry
from app.database.sql_store import sql_store

router = APIRouter(prefix="/api/v1", tags=["Metadata & Catalog"])

@router.get("/datasets")
async def list_datasets():
    """List all structured SQL datasets and tables."""
    datasets = registry.get_all_datasets()
    return {"status": "success", "count": len(datasets), "datasets": datasets}

@router.get("/schemas")
async def get_schema_catalog():
    """Get the full schema catalog with column descriptions."""
    catalog_text = registry.get_full_schema_catalog()
    return {"status": "success", "catalog": catalog_text}

@router.get("/tables/{table_name}")
async def get_table_details(table_name: str, limit: int = 25):
    """Get columns, types, and sample rows for a specific SQL table."""
    columns = registry.get_table_schema(table_name)
    sample_rows = sql_store.get_table_sample(table_name, limit=limit)
    return {
        "status": "success",
        "table_name": table_name,
        "columns": columns,
        "sample_rows": sample_rows
    }
