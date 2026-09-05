import pytest
import pandas as pd
from pathlib import Path
from app.ingestion.detector import detector
from app.ingestion.parsers.document_parser import document_parser
from app.ingestion.parsers.spreadsheet_parser import spreadsheet_parser
from app.ingestion.parsers.code_parser import code_parser
from app.ingestion.chunkers.parent_child import parent_child_chunker
from app.ingestion.chunkers.code_chunker import code_chunker
from app.ingestion.pipeline import ingestion_pipeline

def test_detector_classification(tmp_path):
    md_file = tmp_path / "manual.md"
    md_file.write_text("# Test Manual")
    info = detector.detect(md_file)
    assert info["category"] == "markdown"
    assert info["storage_route"] == "unstructured_document"

    csv_file = tmp_path / "sales.csv"
    csv_file.write_text("id,revenue\n1,100")
    info = detector.detect(csv_file)
    assert info["category"] == "csv"
    assert info["storage_route"] == "spreadsheet"

    py_file = tmp_path / "app.py"
    py_file.write_text("def hello(): pass")
    info = detector.detect(py_file)
    assert info["category"] == "code"
    assert info["storage_route"] == "source_code"

def test_markdown_parent_child_chunking(tmp_path):
    md_text = """# Administration Manual

## Authentication
OAuth requires a client ID and client secret to authenticate applications.
Access tokens expire after 60 minutes.

## Payment Failure Policy
When a payment fails, the subscription enters grace period.
Notify billing department immediately.
"""
    md_file = tmp_path / "admin_manual.md"
    md_file.write_text(md_text, encoding="utf-8")

    sections = document_parser.parse(md_file, "markdown")
    assert len(sections) == 2
    assert "Authentication" in sections[0]["heading_path"]

    children = parent_child_chunker.split_section_into_children(
        section_content=sections[0]["content"],
        document_name=md_file.name,
        heading_path=sections[0]["heading_path"],
        source_id="src_123",
        section_id="sec_123"
    )
    assert len(children) >= 1
    assert "Document: admin_manual.md" in children[0]["embedding_text"]
    assert "Authentication" in children[0]["embedding_text"]
    assert "OAuth requires a client ID" in children[0]["content"]

def test_python_code_symbol_parsing(tmp_path):
    code_text = '''import os
from typing import List

class PaymentProcessor:
    """Handles credit card payments."""
    
    def process_transaction(self, amount: float) -> bool:
        """Charge the given amount."""
        return amount > 0

def calculate_tax(subtotal: float) -> float:
    return subtotal * 0.20
'''
    py_file = tmp_path / "billing.py"
    py_file.write_text(code_text, encoding="utf-8")

    symbols = code_parser.parse(py_file, repository_name="test_repo")
    assert len(symbols) >= 3

    sym_names = [s["symbol_name"] for s in symbols]
    assert "PaymentProcessor" in sym_names
    assert "PaymentProcessor.process_transaction" in sym_names
    assert "calculate_tax" in sym_names

    chunks = code_chunker.chunk_symbols(symbols, "src_code_1", py_file.name)
    assert len(chunks) == len(symbols)
    assert "Repository: test_repo" in chunks[0]["embedding_text"]
    assert "Symbol: PaymentProcessor" in chunks[0]["embedding_text"]

def test_spreadsheet_parser_and_ingestion(tmp_path):
    csv_file = tmp_path / "customer_tickets.csv"
    csv_file.write_text(
        "ticket_id,customer,priority,description\n"
        "1001,Acme Corp,High,Login fails after password reset on portal\n"
        "1002,Beta Inc,Low,Update invoice billing address\n"
    )

    summary = ingestion_pipeline.ingest_file(csv_file, source_id="src_test_csv")
    assert summary["storage_route"] == "spreadsheet"
    assert len(summary["sql_tables_created"]) == 1
    assert summary["chunks_indexed"] >= 1
