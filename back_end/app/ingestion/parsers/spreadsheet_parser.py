from pathlib import Path
from typing import Dict, List, Any, Tuple
import pandas as pd
import re

class SpreadsheetParser:
    """
    Parses CSV and Excel files into structured relational dataframes,
    normalizes table and column names, and identifies long text columns for semantic vector search.
    """
    def parse(self, file_path: Path, source_id: str) -> List[Dict[str, Any]]:
        suffix = file_path.suffix.lower()
        extracted_sheets: List[Dict[str, Any]] = []

        if suffix in [".csv", ".tsv"]:
            sep = "\t" if suffix == ".tsv" else ","
            df = pd.read_csv(file_path, sep=sep)
            sheet_name = file_path.stem
            table_dict = self._process_dataframe(df, file_path.name, sheet_name, source_id)
            extracted_sheets.append(table_dict)
        elif suffix in [".xlsx", ".xls"]:
            excel_file = pd.ExcelFile(file_path)
            for sheet in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet)
                table_dict = self._process_dataframe(df, file_path.name, sheet, source_id)
                extracted_sheets.append(table_dict)

        return extracted_sheets

    def _clean_identifier(self, name: str) -> str:
        clean = re.sub(r'[^a-zA-Z0-9_]', '_', str(name).strip().lower())
        clean = re.sub(r'_+', '_', clean).strip('_')
        return clean or "unnamed"

    def _process_dataframe(
        self,
        df: pd.DataFrame,
        filename: str,
        sheet_name: str,
        source_id: str
    ) -> Dict[str, Any]:
        # Drop completely empty rows and columns
        df = df.dropna(how="all").dropna(axis=1, how="all")
        
        # Clean column names
        cleaned_columns = {}
        for col in df.columns:
            cleaned_columns[col] = self._clean_identifier(col)
        df = df.rename(columns=cleaned_columns)

        # Generate safe SQL table name
        short_id = source_id.replace("-", "")[:8]
        safe_sheet = self._clean_identifier(sheet_name)
        sql_table_name = f"doc_{short_id}_{safe_sheet}"

        # Identify text columns (avg length > 25 chars, max length > 40 chars, or semantic column names)
        text_columns = []
        text_name_hints = {"description", "notes", "summary", "details", "comments", "text", "body", "message", "query", "question", "issue", "content"}
        for col in df.columns:
            col_str = str(col).lower()
            if df[col].dtype == "object":
                sample_lens = df[col].dropna().astype(str).str.len()
                if not sample_lens.empty:
                    if (sample_lens.mean() > 25 or sample_lens.max() > 40 or any(hint in col_str for hint in text_name_hints)):
                        text_columns.append(col)

        return {
            "source_file": filename,
            "sheet_name": sheet_name,
            "sql_table_name": sql_table_name,
            "dataframe": df,
            "columns": list(df.columns),
            "text_columns": text_columns,
            "row_count": len(df)
        }


spreadsheet_parser = SpreadsheetParser()
