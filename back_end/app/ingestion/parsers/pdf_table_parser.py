from pathlib import Path
from typing import List, Dict, Any, Optional
import pdfplumber
import pandas as pd
import re

class PDFTableParser:
    """
    Extracts tabular data from PDF files and creates three distinct representations:
    1. Original table representation (Markdown) for citation and display.
    2. SQL relational table for numeric queries, counting, and aggregation.
    3. Search description for vector discovery.
    """
    def extract_tables(self, file_path: Path, source_id: str) -> List[Dict[str, Any]]:
        extracted: List[Dict[str, Any]] = []
        short_id = source_id.replace("-", "")[:8]

        try:
            with pdfplumber.open(str(file_path)) as pdf:
                table_idx = 0
                for page_num, page in enumerate(pdf.pages, start=1):
                    tables = page.extract_tables()
                    for t in tables:
                        if not t or len(t) < 2:
                            continue
                        
                        # First row as header
                        raw_headers = t[0]
                        rows = t[1:]
                        
                        # Normalize headers
                        headers = []
                        for idx, h in enumerate(raw_headers):
                            header_name = str(h).strip() if h else f"col_{idx+1}"
                            clean_h = re.sub(r'[^a-zA-Z0-9_]', '_', header_name.lower()).strip('_')
                            headers.append(clean_h or f"col_{idx+1}")

                        df = pd.DataFrame(rows, columns=headers)
                        df = df.dropna(how="all")
                        if df.empty:
                            continue

                        table_idx += 1
                        table_name = f"doc_{short_id}_pdf_table_{page_num}_{table_idx}"
                        
                        # 1. Original Markdown Table representation
                        md_table = df.to_markdown(index=False)

                        # 2. Textual Search Description
                        col_list_str = ", ".join(headers)
                        description = (
                            f"Table from {file_path.name} (Page {page_num}). "
                            f"Contains columns: {col_list_str}. "
                            f"Rows count: {len(df)}."
                        )

                        extracted.append({
                            "table_id": f"{source_id}_tbl_{page_num}_{table_idx}",
                            "source_id": source_id,
                            "sql_table_name": table_name,
                            "page_number": page_num,
                            "raw_markdown": md_table,
                            "search_description": description,
                            "dataframe": df,
                            "headers": headers
                        })
        except Exception as e:
            pass

        return extracted


pdf_table_parser = PDFTableParser()
