import re
import sqlite3
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from app.config import settings
from app.core.logging import app_logger

class SQLStore:
    """
    SQL storage engine for structured datasets (CSV, Excel, extracted PDF tables, JSON tables).
    Enforces safe table creation, indexing, and strictly validated read-only execution.
    """
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = str(db_path or settings.sqlite_db_path)

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def sanitize_identifier(self, name: str) -> str:
        """Clean table and column names to safe SQL identifiers (lowercase, alphanumeric + underscore)."""
        clean = re.sub(r'[^a-zA-Z0-9_]', '_', name.strip().lower())
        clean = re.sub(r'_+', '_', clean).strip('_')
        if not clean or clean[0].isdigit():
            clean = f"col_{clean}"
        return clean

    def load_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        add_row_id: bool = True
    ) -> Tuple[str, List[str]]:
        """
        Loads a pandas DataFrame into SQLite table with normalized column names and types.
        Returns (sanitized_table_name, sanitized_columns).
        """
        sanitized_table = self.sanitize_identifier(table_name)
        
        # Clean columns
        clean_cols = {}
        for col in df.columns:
            clean_cols[col] = self.sanitize_identifier(str(col))
        df = df.rename(columns=clean_cols)
        
        if add_row_id and "row_id" not in df.columns:
            df.insert(0, "row_id", range(1, len(df) + 1))

        with self.get_connection() as conn:
            # Write dataframe to table
            df.to_sql(sanitized_table, conn, if_exists="replace", index=False)
            cursor = conn.cursor()
            
            # Create primary index on row_id if present
            if "row_id" in df.columns:
                try:
                    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{sanitized_table}_row_id ON {sanitized_table} (row_id);")
                except Exception as e:
                    app_logger.log_state(f"Index creation notice: {e}", step="sql_store", level="warning")
            
            # Create indexes on potential category/filter columns
            for col in df.columns:
                if col != "row_id" and df[col].nunique() < len(df) * 0.5:
                    try:
                        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{sanitized_table}_{col} ON {sanitized_table} ({col});")
                    except Exception:
                        pass

            conn.commit()

        return sanitized_table, list(df.columns)

    def execute_read_only(
        self,
        sql: str,
        max_rows: int = 100,
        trace_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Execute read-only SQL query with connection isolation and row limits.
        """
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            # Set query execution timeout
            cursor.execute("PRAGMA busy_timeout = 3000;")
            cursor.execute(sql)
            rows = cursor.fetchmany(max_rows)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            results = [dict(r) for r in rows]
            return results, columns
        finally:
            conn.close()

    def get_table_sample(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        clean_table = self.sanitize_identifier(table_name)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {clean_table} LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def get_row_by_id(self, table_name: str, row_id: Any) -> Optional[Dict[str, Any]]:
        clean_table = self.sanitize_identifier(table_name)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {clean_table} WHERE row_id = ?", (row_id,))
            row = cursor.fetchone()
            return dict(row) if row else None


sql_store = SQLStore()
