import sqlite3
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path
from app.config import settings
from app.core.logging import app_logger

def _now_iso() -> str:
    try:
        return datetime.now(timezone.utc).isoformat()
    except Exception:
        return datetime.now().isoformat()

class DocumentRegistry:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = str(db_path or settings.sqlite_db_path)
        self.init_schema()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Sources Registry Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                source_type TEXT NOT NULL,
                owner_id TEXT DEFAULT 'system',
                version TEXT DEFAULT '1.0',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 2. Dataset Metadata Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS dataset_metadata (
                dataset_id TEXT PRIMARY KEY,
                source_file TEXT NOT NULL,
                sheet_name TEXT,
                sql_table_name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 3. Column Metadata Catalog
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS column_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                column_name TEXT NOT NULL,
                data_type TEXT NOT NULL,
                description TEXT,
                sample_values TEXT,
                is_filterable BOOLEAN DEFAULT 1,
                is_aggregatable BOOLEAN DEFAULT 0,
                UNIQUE(table_name, column_name)
            );
            """)

            # 4. Extracted Tables from Documents (e.g. PDFs)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS extracted_tables (
                table_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                table_name TEXT NOT NULL,
                description TEXT,
                page_number INTEGER,
                raw_markdown TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES sources (source_id)
            );
            """)

            # 5. Document Sections (Parents)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_sections (
                section_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                heading_path TEXT NOT NULL,
                content TEXT NOT NULL,
                section_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES sources (source_id)
            );
            """)

            # 6. Document Chunks (Children)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                chunk_id TEXT PRIMARY KEY,
                section_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                child_index INTEGER DEFAULT 0,
                content TEXT NOT NULL,
                embedding_text TEXT NOT NULL,
                token_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (section_id) REFERENCES document_sections (section_id),
                FOREIGN KEY (source_id) REFERENCES sources (source_id)
            );
            """)

            conn.commit()

    def register_source(
        self,
        source_id: str,
        filename: str,
        mime_type: str,
        source_type: str,
        owner_id: str = "default_user",
        version: str = "1.0"
    ):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO sources (source_id, filename, mime_type, source_type, owner_id, version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (source_id, filename, mime_type, source_type, owner_id, version, _now_iso()))
            conn.commit()

    def register_dataset(
        self,
        dataset_id: str,
        source_file: str,
        sheet_name: Optional[str],
        sql_table_name: str,
        description: str
    ):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO dataset_metadata (dataset_id, source_file, sheet_name, sql_table_name, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (dataset_id, source_file, sheet_name, sql_table_name, description, _now_iso()))
            conn.commit()

    def register_column_metadata(
        self,
        table_name: str,
        column_name: str,
        data_type: str,
        description: str,
        sample_values: List[Any],
        is_filterable: bool = True,
        is_aggregatable: bool = False
    ):
        samples_str = json.dumps(sample_values[:5], default=str)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO column_metadata 
            (table_name, column_name, data_type, description, sample_values, is_filterable, is_aggregatable)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (table_name, column_name, data_type, description, samples_str, 1 if is_filterable else 0, 1 if is_aggregatable else 0))
            conn.commit()

    def register_extracted_table(
        self,
        table_id: str,
        source_id: str,
        table_name: str,
        description: str,
        page_number: int,
        raw_markdown: str
    ):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO extracted_tables (table_id, source_id, table_name, description, page_number, raw_markdown, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (table_id, source_id, table_name, description, page_number, raw_markdown, _now_iso()))
            conn.commit()

    def save_section(
        self,
        section_id: str,
        source_id: str,
        heading_path: str,
        content: str,
        section_order: int = 0
    ):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO document_sections (section_id, source_id, heading_path, content, section_order, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (section_id, source_id, heading_path, content, section_order, _now_iso()))
            conn.commit()

    def save_chunk(
        self,
        chunk_id: str,
        section_id: str,
        source_id: str,
        child_index: int,
        content: str,
        embedding_text: str,
        token_count: int = 0
    ):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO document_chunks (chunk_id, section_id, source_id, child_index, content, embedding_text, token_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (chunk_id, section_id, source_id, child_index, content, embedding_text, token_count, _now_iso()))
            conn.commit()

    def get_section(self, section_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM document_sections WHERE section_id = ?", (section_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_sources(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sources ORDER BY created_at DESC")
            return [dict(r) for r in cursor.fetchall()]

    def get_all_datasets(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM dataset_metadata ORDER BY created_at DESC")
            return [dict(r) for r in cursor.fetchall()]

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM column_metadata WHERE table_name = ?", (table_name,))
            return [dict(r) for r in cursor.fetchall()]

    def get_full_schema_catalog(self) -> str:
        datasets = self.get_all_datasets()
        catalog_lines = []
        for ds in datasets:
            tname = ds["sql_table_name"]
            catalog_lines.append(f"Table: {tname} (Source: {ds['source_file']}, Sheet: {ds.get('sheet_name', 'N/A')})")
            catalog_lines.append(f"  Description: {ds.get('description', '')}")
            cols = self.get_table_schema(tname)
            for c in cols:
                filt = "filterable" if c.get("is_filterable") else ""
                agg = "aggregatable" if c.get("is_aggregatable") else ""
                flags = f"[{', '.join(filter(None, [filt, agg]))}]" if filt or agg else ""
                catalog_lines.append(f"  - {c['column_name']} ({c['data_type']}): {c.get('description', '')} {flags} (e.g. {c.get('sample_values')})")
            catalog_lines.append("")
        return "\n".join(catalog_lines)


registry = DocumentRegistry()
