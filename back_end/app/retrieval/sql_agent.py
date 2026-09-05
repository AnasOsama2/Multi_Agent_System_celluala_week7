import re
from typing import Dict, Any, List, Optional, Tuple
import sqlparse
from app.core.llm import llm_client
from app.core.logging import app_logger
from app.database.registry import registry
from app.database.sql_store import sql_store

class SQLAgent:
    """
    Safe, read-only SQL agent that retrieves schema, generates SQLite SQL,
    validates for security compliance, executes read-only queries, and summarizes results.
    """
    FORBIDDEN_KEYWORDS = [
        r'\bDROP\b', r'\bDELETE\b', r'\bUPDATE\b', r'\bINSERT\b',
        r'\bALTER\b', r'\bCREATE\b', r'\bTRUNCATE\b', r'\bATTACH\b',
        r'\bDETACH\b', r'\bPRAGMA\b', r'\bREPLACE\b', r'\bGRANT\b',
        r'\bREVOKE\b', r'\bVACUUM\b', r'\bEXEC\b', r'\bEXECUTE\b'
    ]

    def validate_sql(self, sql: str) -> Tuple[bool, str, str]:
        """
        Validates SQL for safety:
        1. Checks for forbidden mutating keywords.
        2. Ensures it starts with SELECT or WITH.
        3. Enforces a LIMIT clause.
        Returns (is_valid, sanitized_sql, error_message).
        """
        clean_sql = sql.strip().rstrip(";")
        
        # Check forbidden keywords
        for kw_pattern in self.FORBIDDEN_KEYWORDS:
            if re.search(kw_pattern, clean_sql, re.IGNORECASE):
                return False, "", f"Forbidden SQL operation detected ({kw_pattern})"

        # Check statement type
        parsed = sqlparse.parse(clean_sql)
        if not parsed:
            return False, "", "Empty or unparseable SQL"

        first_token = parsed[0].get_type()
        if first_token not in ["SELECT", "UNKNOWN"]:
            # Check if starts with SELECT or WITH
            if not re.match(r'^(SELECT|WITH)\b', clean_sql, re.IGNORECASE):
                return False, "", f"Only SELECT or WITH queries are permitted (got {first_token})"

        # Enforce LIMIT
        if not re.search(r'\bLIMIT\s+\d+\b', clean_sql, re.IGNORECASE):
            clean_sql = f"{clean_sql} LIMIT 100"

        return True, clean_sql, "Valid"

    def execute_query(
        self,
        user_query: str,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Full SQL generation and execution pipeline:
        Find schema -> Generate SQL -> Validate -> Execute -> Summarize.
        """
        catalog = registry.get_full_schema_catalog()
        if not catalog.strip():
            return {
                "success": False,
                "error": "No SQL tables or datasets currently registered in database.",
                "rows": [],
                "sql": ""
            }

        prompt = f"""
You are an expert SQLite data analyst. Given the database schema below and user question, write a valid SQLite SELECT query.

Database Schema Catalog:
{catalog}

User Question: "{user_query}"

Rules:
1. Write ONLY a read-only SQLite SELECT query.
2. Use exact table names and column names from the schema catalog.
3. For case-insensitive text matches, use `LIKE '%term%'` or `LOWER(col) = LOWER('term')`.
4. Enforce reasonable aggregations (COUNT, SUM, AVG, MIN, MAX) when asked.
5. Return JSON with keys: "sql", "explanation".

JSON format:
{{
  "sql": "SELECT ... FROM ... WHERE ...",
  "explanation": "why this query answers the question"
}}
"""
        try:
            res = llm_client.generate_json(
                messages=[
                    {"role": "system", "content": "You generate precise SQLite queries. Output strict JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                trace_id=trace_id
            )
            raw_sql = res.get("sql", "").strip()
            explanation = res.get("explanation", "")
        except Exception as e:
            return {"success": False, "error": f"SQL generation error: {e}", "rows": [], "sql": ""}

        # Validate SQL
        is_valid, safe_sql, val_msg = self.validate_sql(raw_sql)
        if not is_valid:
            app_logger.log_sql_execution(user_query, raw_sql, f"REJECTED: {val_msg}", 0, trace_id)
            return {
                "success": False,
                "error": f"SQL Validation Failed: {val_msg}",
                "generated_sql": raw_sql,
                "rows": []
            }

        # Execute
        try:
            rows, columns = sql_store.execute_read_only(safe_sql, max_rows=100, trace_id=trace_id)
            app_logger.log_sql_execution(user_query, safe_sql, "PASSED", len(rows), trace_id)
            
            # Format row summary
            summary = self._format_result_summary(rows, columns)
            
            return {
                "success": True,
                "sql": safe_sql,
                "explanation": explanation,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "summary": summary
            }
        except Exception as e:
            app_logger.log_sql_execution(user_query, safe_sql, f"EXECUTION ERROR: {e}", 0, trace_id)
            return {
                "success": False,
                "error": f"Database execution error: {e}",
                "sql": safe_sql,
                "rows": []
            }

    def _format_result_summary(self, rows: List[Dict[str, Any]], columns: List[str]) -> str:
        if not rows:
            return "No matching rows found in dataset."
        if len(rows) == 1 and len(columns) == 1:
            col = columns[0]
            val = rows[0][col]
            return f"Result: {col} = {val}"
        
        # Small markdown table for prompt injection
        header = " | ".join(columns)
        separator = " | ".join(["---"] * len(columns))
        row_lines = []
        for r in rows[:15]:
            row_lines.append(" | ".join(str(r.get(c, "")) for c in columns))
        
        table_str = f"| {header} |\n| {separator} |\n" + "\n".join(f"| {r} |" for r in row_lines)
        if len(rows) > 15:
            table_str += f"\n\n*(Showing top 15 of {len(rows)} returned rows)*"
        return table_str


sql_agent = SQLAgent()
