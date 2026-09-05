from typing import List, Dict, Any
from app.database.registry import registry
from app.database.sql_store import sql_store

class ParentContextExpander:
    """
    Expands retrieved child chunks to full parent section context or complete SQL rows,
    and builds formatted provenance citations.
    """
    def expand(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        expanded_blocks: List[str] = []
        citations: List[Dict[str, Any]] = []

        seen_sections = set()
        seen_rows = set()

        for idx, cand in enumerate(candidates, start=1):
            meta = cand.get("metadata", {})
            content = cand.get("content", "")
            
            # Case 1: Spreadsheet Table Row
            if meta.get("is_table_row"):
                table_name = meta.get("table_name", "")
                row_id = meta.get("row_id")
                source_file = meta.get("source_file", "")
                row_key = f"{table_name}_{row_id}"

                if row_key not in seen_rows:
                    seen_rows.add(row_key)
                    # Fetch complete row from SQL
                    full_row = sql_store.get_row_by_id(table_name, row_id) if row_id is not None else None
                    
                    citation_text = f"Source: {source_file}, Table: {table_name}, Row ID: {row_id}"
                    citations.append({
                        "type": "table_row",
                        "source_file": source_file,
                        "table_name": table_name,
                        "row_id": row_id,
                        "citation": citation_text
                    })

                    block = (
                        f"### Reference [{idx}]: {citation_text}\n"
                        f"**Matching Field ({meta.get('column_name', 'text')}):** {content}\n"
                        f"**Full Record Data:**\n```json\n{full_row or {}}\n```\n"
                    )
                    expanded_blocks.append(block)

            # Case 2: Extracted PDF Table
            elif meta.get("is_pdf_table"):
                table_name = meta.get("table_name", "")
                source_file = meta.get("source_file", "")
                page_num = meta.get("page_number", 1)
                
                citation_text = f"Source: {source_file}, Page: {page_num}, Table: {table_name}"
                citations.append({
                    "type": "extracted_table",
                    "source_file": source_file,
                    "page_number": page_num,
                    "table_name": table_name,
                    "citation": citation_text
                })

                block = (
                    f"### Reference [{idx}]: {citation_text}\n"
                    f"{content}\n"
                )
                expanded_blocks.append(block)

            # Case 3: Source Code Symbol
            elif meta.get("symbol_name"):
                source_file = meta.get("source_file", "")
                symbol_name = meta.get("symbol_name", "")
                sig = meta.get("signature", "")
                l_start = meta.get("line_start", 1)
                l_end = meta.get("line_end", 1)

                citation_text = f"Source: {source_file}, Symbol: {symbol_name} (Lines {l_start}–{l_end})"
                citations.append({
                    "type": "code_symbol",
                    "source_file": source_file,
                    "symbol_name": symbol_name,
                    "signature": sig,
                    "lines": f"{l_start}-{l_end}",
                    "citation": citation_text
                })

                block = (
                    f"### Reference [{idx}]: {citation_text}\n"
                    f"**Signature:** `{sig}`\n"
                    f"```\n{content}\n```\n"
                )
                expanded_blocks.append(block)

            # Case 4: Parent-Child Document Section
            else:
                sec_id = meta.get("section_id")
                source_file = meta.get("source_file", "")
                heading_path = meta.get("heading_path", "Document Section")
                
                parent_sec = registry.get_section(sec_id) if sec_id else None
                parent_content = parent_sec.get("content") if parent_sec else content
                
                sec_key = sec_id or f"{source_file}_{heading_path}"
                if sec_key not in seen_sections:
                    seen_sections.add(sec_key)
                    
                    citation_text = f"Source: {source_file}, Section: {heading_path}"
                    citations.append({
                        "type": "document_section",
                        "source_file": source_file,
                        "heading_path": heading_path,
                        "citation": citation_text
                    })

                    block = (
                        f"### Reference [{idx}]: {citation_text}\n"
                        f"**Relevant Heading Context:** {heading_path}\n"
                        f"**Section Content:**\n{parent_content}\n"
                    )
                    expanded_blocks.append(block)

        combined_context = "\n\n".join(expanded_blocks)
        return {
            "context_text": combined_context,
            "citations": citations
        }


parent_expander = ParentContextExpander()
