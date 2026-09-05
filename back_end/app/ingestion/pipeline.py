import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from app.config import settings
from app.core.logging import app_logger
from app.database.registry import registry
from app.database.sql_store import sql_store
from app.database.vector_store import vector_store
from app.ingestion.detector import detector
from app.ingestion.parsers.document_parser import document_parser
from app.ingestion.parsers.spreadsheet_parser import spreadsheet_parser
from app.ingestion.parsers.pdf_table_parser import pdf_table_parser
from app.ingestion.parsers.json_xml_parser import json_xml_parser
from app.ingestion.parsers.code_parser import code_parser
from app.ingestion.chunkers.parent_child import parent_child_chunker
from app.ingestion.chunkers.code_chunker import code_chunker
from app.ingestion.schema_generator import schema_generator

class IngestionPipeline:
    """
    Unified multimodal document loading and indexing pipeline.
    Routes unstructured text, spreadsheets, PDF tables, JSON/XML, and code
    to optimal storage engines (SQLite, ChromaDB, BM25) following strict chunking rules.
    """
    def ingest_file(
        self,
        file_path: Path,
        source_id: Optional[str] = None,
        owner_id: str = "default_user",
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        source_id = source_id or str(uuid.uuid4())
        file_info = detector.detect(file_path)
        category = file_info["category"]
        storage_route = file_info["storage_route"]

        app_logger.log_state(
            event=f"Ingesting file '{file_path.name}' (Category: {category}, Route: {storage_route})",
            step="ingestion_pipeline",
            details=file_info,
            trace_id=trace_id
        )

        # 1. Register Source
        registry.register_source(
            source_id=source_id,
            filename=file_path.name,
            mime_type=file_info["mime_type"],
            source_type=category,
            owner_id=owner_id
        )

        result_summary = {
            "source_id": source_id,
            "filename": file_path.name,
            "category": category,
            "storage_route": storage_route,
            "sql_tables_created": [],
            "chunks_indexed": 0,
            "sections_created": 0
        }

        # 2. Route by category
        if storage_route == "spreadsheet":
            self._ingest_spreadsheet(file_path, source_id, result_summary, trace_id)
        elif storage_route == "structured_data":
            self._ingest_structured_data(file_path, source_id, result_summary, trace_id)
        elif storage_route == "source_code":
            self._ingest_code(file_path, source_id, result_summary, trace_id)
        elif category == "pdf":
            self._ingest_pdf(file_path, source_id, result_summary, trace_id)
        else:
            self._ingest_unstructured(file_path, category, source_id, result_summary, trace_id)

        app_logger.log_state(
            event=f"Completed ingestion for '{file_path.name}': {result_summary['chunks_indexed']} chunks, {len(result_summary['sql_tables_created'])} SQL tables",
            step="ingestion_pipeline",
            details=result_summary,
            trace_id=trace_id
        )

        return result_summary

    def _ingest_spreadsheet(
        self,
        file_path: Path,
        source_id: str,
        summary: Dict[str, Any],
        trace_id: Optional[str]
    ):
        sheets = spreadsheet_parser.parse(file_path, source_id)
        for s in sheets:
            df = s["dataframe"]
            raw_table_name = s["sql_table_name"]
            
            # Load into SQLite
            table_name, cols = sql_store.load_dataframe(df, raw_table_name, add_row_id=True)
            summary["sql_tables_created"].append(table_name)

            # Generate and register schema & column metadata
            schema_generator.generate_and_save_metadata(
                table_name=table_name,
                source_file=file_path.name,
                sheet_name=s.get("sheet_name"),
                df=df,
                source_id=source_id,
                trace_id=trace_id
            )

            # Index long text columns for semantic row search
            text_cols = s.get("text_columns", [])
            if text_cols:
                chunk_ids = []
                emb_texts = []
                contents = []
                metas = []

                for row_idx, (_, row) in enumerate(df.iterrows(), start=1):
                    row_id = row.get("row_id", row_idx)
                    for col in text_cols:
                        val = str(row[col]) if pd.notna(row[col]) else ""
                        if val.strip():
                            cid = f"row_{source_id[:8]}_{table_name}_{row_id}_{col}"
                            emb_text = f"Dataset: {file_path.name}\nTable: {table_name}\nColumn: {col}\nRow ID: {row_id}\n\nContent:\n{val}"
                            
                            chunk_ids.append(cid)
                            emb_texts.append(emb_text)
                            contents.append(val)
                            metas.append({
                                "source_id": source_id,
                                "source_file": file_path.name,
                                "table_name": table_name,
                                "column_name": col,
                                "row_id": int(row_id),
                                "is_table_row": True
                            })

                if chunk_ids:
                    vector_store.add_chunks(chunk_ids, emb_texts, contents, metas, trace_id=trace_id)
                    summary["chunks_indexed"] += len(chunk_ids)

    def _ingest_structured_data(
        self,
        file_path: Path,
        source_id: str,
        summary: Dict[str, Any],
        trace_id: Optional[str]
    ):
        tables = json_xml_parser.parse(file_path, source_id)
        for t in tables:
            df = t["dataframe"]
            raw_table_name = t["sql_table_name"]
            
            table_name, cols = sql_store.load_dataframe(df, raw_table_name, add_row_id=True)
            summary["sql_tables_created"].append(table_name)

            schema_generator.generate_and_save_metadata(
                table_name=table_name,
                source_file=file_path.name,
                sheet_name=t.get("sheet_name"),
                df=df,
                source_id=source_id,
                trace_id=trace_id
            )

    def _ingest_code(
        self,
        file_path: Path,
        source_id: str,
        summary: Dict[str, Any],
        trace_id: Optional[str]
    ):
        symbols = code_parser.parse(file_path, repository_name="workspace")
        chunks = code_chunker.chunk_symbols(symbols, source_id, file_path.name)
        
        chunk_ids = [c["chunk_id"] for c in chunks]
        emb_texts = [c["embedding_text"] for c in chunks]
        contents = [c["content"] for c in chunks]
        metas = [c["metadata"] for c in chunks]

        if chunk_ids:
            vector_store.add_chunks(chunk_ids, emb_texts, contents, metas, trace_id=trace_id)
            summary["chunks_indexed"] += len(chunk_ids)

    def _ingest_pdf(
        self,
        file_path: Path,
        source_id: str,
        summary: Dict[str, Any],
        trace_id: Optional[str]
    ):
        # 1. Extract PDF Tables
        tables = pdf_table_parser.extract_tables(file_path, source_id)
        for t in tables:
            df = t["dataframe"]
            raw_table_name = t["sql_table_name"]
            
            table_name, cols = sql_store.load_dataframe(df, raw_table_name, add_row_id=True)
            summary["sql_tables_created"].append(table_name)

            # Register extracted table for citations
            registry.register_extracted_table(
                table_id=t["table_id"],
                source_id=source_id,
                table_name=table_name,
                description=t["search_description"],
                page_number=t["page_number"],
                raw_markdown=t["raw_markdown"]
            )

            # Register metadata
            schema_generator.generate_and_save_metadata(
                table_name=table_name,
                source_file=file_path.name,
                sheet_name=f"Page_{t['page_number']}_Table",
                df=df,
                source_id=source_id,
                trace_id=trace_id
            )

            # Vector index search description for table retrieval
            cid = f"table_desc_{t['table_id']}"
            vector_store.add_chunks(
                chunk_ids=[cid],
                embedding_texts=[t["search_description"]],
                contents=[t["raw_markdown"]],
                metadatas=[{
                    "source_id": source_id,
                    "source_file": file_path.name,
                    "table_name": table_name,
                    "is_pdf_table": True,
                    "page_number": t["page_number"]
                }],
                trace_id=trace_id
            )
            summary["chunks_indexed"] += 1

        # 2. Ingest document text with parent-child chunking
        self._ingest_unstructured(file_path, "pdf", source_id, summary, trace_id)

    def _ingest_unstructured(
        self,
        file_path: Path,
        category: str,
        source_id: str,
        summary: Dict[str, Any],
        trace_id: Optional[str]
    ):
        sections = document_parser.parse(file_path, category)
        summary["sections_created"] = len(sections)

        chunk_ids = []
        emb_texts = []
        contents = []
        metas = []

        for idx, sec in enumerate(sections):
            sec_id = f"sec_{source_id[:8]}_{idx+1}"
            heading = sec.get("heading_path", file_path.stem)
            content = sec.get("content", "")

            # Save parent section in SQLite
            registry.save_section(
                section_id=sec_id,
                source_id=source_id,
                heading_path=heading,
                content=content,
                section_order=idx
            )

            # Split into child chunks
            children = parent_child_chunker.split_section_into_children(
                section_content=content,
                document_name=file_path.name,
                heading_path=heading,
                source_id=source_id,
                section_id=sec_id
            )

            for child in children:
                cid = child["chunk_id"]
                c_content = child["content"]
                c_emb = child["embedding_text"]

                # Save chunk in SQLite
                registry.save_chunk(
                    chunk_id=cid,
                    section_id=sec_id,
                    source_id=source_id,
                    child_index=child["child_index"],
                    content=c_content,
                    embedding_text=c_emb,
                    token_count=child["token_count"]
                )

                chunk_ids.append(cid)
                emb_texts.append(c_emb)
                contents.append(c_content)
                metas.append({
                    "source_id": source_id,
                    "source_file": file_path.name,
                    "section_id": sec_id,
                    "heading_path": heading,
                    "child_index": child["child_index"]
                })

        if chunk_ids:
            vector_store.add_chunks(chunk_ids, emb_texts, contents, metas, trace_id=trace_id)
            summary["chunks_indexed"] += len(chunk_ids)


ingestion_pipeline = IngestionPipeline()
