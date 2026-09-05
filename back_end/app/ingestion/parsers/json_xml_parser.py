import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Tuple
import pandas as pd
import re

class JsonXmlParser:
    """
    Parses JSON and XML files:
    - Flat lists of objects -> Relational SQL tables.
    - Nested structures -> Relational tables or structured document hierarchy.
    - Long text fields -> Separate vector indexing.
    """
    def parse(self, file_path: Path, source_id: str) -> List[Dict[str, Any]]:
        suffix = file_path.suffix.lower()
        if suffix == ".json":
            return self.parse_json(file_path, source_id)
        elif suffix == ".xml":
            return self.parse_xml(file_path, source_id)
        return []

    def _clean_identifier(self, name: str) -> str:
        clean = re.sub(r'[^a-zA-Z0-9_]', '_', str(name).strip().lower())
        clean = re.sub(r'_+', '_', clean).strip('_')
        return clean or "field"

    def parse_json(self, file_path: Path, source_id: str) -> List[Dict[str, Any]]:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        tables: List[Dict[str, Any]] = []
        short_id = source_id.replace("-", "")[:8]

        if isinstance(data, list):
            # List of records
            if all(isinstance(item, dict) for item in data):
                df = pd.json_normalize(data)
                # Clean columns
                df = df.rename(columns={c: self._clean_identifier(c) for c in df.columns})
                table_name = f"doc_{short_id}_{self._clean_identifier(file_path.stem)}"
                
                text_columns = [
                    c for c in df.columns 
                    if df[c].dtype == "object" and df[c].dropna().astype(str).str.len().mean() > 40
                ]

                tables.append({
                    "source_file": file_path.name,
                    "sheet_name": file_path.stem,
                    "sql_table_name": table_name,
                    "dataframe": df,
                    "columns": list(df.columns),
                    "text_columns": text_columns,
                    "row_count": len(df)
                })
        elif isinstance(data, dict):
            # Check for top-level arrays (e.g. {"users": [...], "orders": [...]})
            for key, val in data.items():
                if isinstance(val, list) and all(isinstance(item, dict) for item in val):
                    df = pd.json_normalize(val)
                    df = df.rename(columns={c: self._clean_identifier(c) for c in df.columns})
                    table_name = f"doc_{short_id}_{self._clean_identifier(key)}"
                    
                    text_columns = [
                        c for c in df.columns 
                        if df[c].dtype == "object" and df[c].dropna().astype(str).str.len().mean() > 40
                    ]

                    tables.append({
                        "source_file": file_path.name,
                        "sheet_name": key,
                        "sql_table_name": table_name,
                        "dataframe": df,
                        "columns": list(df.columns),
                        "text_columns": text_columns,
                        "row_count": len(df)
                    })
                elif isinstance(val, dict):
                    df = pd.json_normalize([val])
                    df = df.rename(columns={c: self._clean_identifier(c) for c in df.columns})
                    table_name = f"doc_{short_id}_{self._clean_identifier(key)}"
                    tables.append({
                        "source_file": file_path.name,
                        "sheet_name": key,
                        "sql_table_name": table_name,
                        "dataframe": df,
                        "columns": list(df.columns),
                        "text_columns": [],
                        "row_count": 1
                    })

        return tables

    def parse_xml(self, file_path: Path, source_id: str) -> List[Dict[str, Any]]:
        tree = ET.parse(file_path)
        root = tree.getroot()

        rows = []
        for child in root:
            row_dict = {}
            for elem in child:
                row_dict[self._clean_identifier(elem.tag)] = elem.text
            if row_dict:
                rows.append(row_dict)

        if not rows:
            return []

        df = pd.DataFrame(rows)
        short_id = source_id.replace("-", "")[:8]
        table_name = f"doc_{short_id}_{self._clean_identifier(root.tag)}"

        text_columns = [
            c for c in df.columns 
            if df[c].dropna().astype(str).str.len().mean() > 40
        ]

        return [{
            "source_file": file_path.name,
            "sheet_name": root.tag,
            "sql_table_name": table_name,
            "dataframe": df,
            "columns": list(df.columns),
            "text_columns": text_columns,
            "row_count": len(df)
        }]


json_xml_parser = JsonXmlParser()
