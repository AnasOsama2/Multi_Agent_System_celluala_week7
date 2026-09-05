import json
import pandas as pd
from typing import Dict, List, Any, Optional
from app.core.llm import llm_client
from app.core.logging import app_logger
from app.database.registry import registry

class SchemaGenerator:
    """
    Analyzes relational tables and generates schema descriptions and column catalog metadata
    using LLM and statistical heuristics.
    """
    def generate_and_save_metadata(
        self,
        table_name: str,
        source_file: str,
        sheet_name: Optional[str],
        df: pd.DataFrame,
        source_id: str,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        
        # Prepare sample data dictionary
        samples = {}
        dtypes = {}
        for col in df.columns:
            non_nulls = df[col].dropna().tolist()
            samples[col] = non_nulls[:3]
            dtypes[col] = str(df[col].dtype)

        # Generate descriptions using LLM
        prompt = f"""
You are a data architect. Given a table '{table_name}' from file '{source_file}' (Sheet: '{sheet_name or "default"}'):
Columns and sample values:
{json.dumps({col: {"dtype": dtypes[col], "samples": samples[col]} for col in df.columns}, default=str, indent=2)}

Generate a JSON object with:
1. "table_description": A 1-2 sentence summary of what this dataset represents.
2. "columns": A map of column_name to object:
   - "description": Clear explanation of what the column represents (e.g. "Numeric order amount in USD").
   - "is_filterable": boolean (true if categorical, ID, status, date, or code).
   - "is_aggregatable": boolean (true if numeric metric like revenue, quantity, price, score, count).

Return ONLY valid JSON matching this schema:
{{
  "table_description": "...",
  "columns": {{
    "column_name": {{
      "description": "...",
      "is_filterable": true,
      "is_aggregatable": false
    }}
  }}
}}
"""
        try:
            res = llm_client.generate_json(
                messages=[
                    {"role": "system", "content": "You are an expert data catalog generator. Output strict JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                trace_id=trace_id
            )
            table_desc = res.get("table_description", f"Dataset from {source_file}")
            col_meta_dict = res.get("columns", {})
        except Exception as e:
            app_logger.log_state(f"LLM Schema generation fallback ({e})", step="schema_gen", level="warning", trace_id=trace_id)
            table_desc = f"Table {table_name} containing {len(df)} rows from {source_file}"
            col_meta_dict = {}

        # Save dataset metadata
        dataset_id = f"ds_{source_id[:8]}_{table_name}"
        registry.register_dataset(
            dataset_id=dataset_id,
            source_file=source_file,
            sheet_name=sheet_name,
            sql_table_name=table_name,
            description=table_desc
        )

        # Save column metadata
        for col in df.columns:
            meta = col_meta_dict.get(col, {})
            desc = meta.get("description", f"Column '{col}' with {dtypes[col]} values")
            
            # Heuristics if LLM missed
            is_num = pd.api.types.is_numeric_dtype(df[col])
            is_filt = meta.get("is_filterable", True)
            is_agg = meta.get("is_aggregatable", is_num and col != "row_id")

            registry.register_column_metadata(
                table_name=table_name,
                column_name=col,
                data_type=dtypes[col],
                description=desc,
                sample_values=samples[col],
                is_filterable=is_filt,
                is_aggregatable=is_agg
            )

        return {
            "table_name": table_name,
            "description": table_desc,
            "columns": col_meta_dict
        }


schema_generator = SchemaGenerator()
