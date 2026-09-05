import ast
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

class CodeParser:
    """
    Parses source code into symbol-level chunks:
    Extracts Classes, Methods, Functions, Signatures, Imports, Docstrings, and Line Ranges.
    """
    def parse(self, file_path: Path, repository_name: str = "project") -> List[Dict[str, Any]]:
        suffix = file_path.suffix.lower()
        if suffix == ".py":
            return self.parse_python(file_path, repository_name)
        else:
            return self.parse_generic_code(file_path, repository_name)

    def parse_python(self, file_path: Path, repository_name: str) -> List[Dict[str, Any]]:
        code_text = file_path.read_text(encoding="utf-8", errors="replace")
        lines = code_text.splitlines()
        
        try:
            tree = ast.parse(code_text, filename=str(file_path))
        except Exception:
            return self.parse_generic_code(file_path, repository_name)

        # Extract top-level imports
        imports = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                imports.extend([alias.name for alias in node.names])
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                imports.extend([f"{mod}.{alias.name}" for alias in node.names])
        imports_str = ", ".join(imports)

        symbols: List[Dict[str, Any]] = []

        def get_source_segment(start_line: int, end_line: int) -> str:
            return "\n".join(lines[start_line - 1:end_line])

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                class_doc = ast.get_docstring(node) or ""
                
                # Class chunk
                class_start = node.lineno
                class_end = getattr(node, "end_lineno", class_start + len(node.body))
                class_code = get_source_segment(class_start, min(class_end, len(lines)))

                symbols.append({
                    "repository": repository_name,
                    "file_path": str(file_path.name),
                    "language": "python",
                    "symbol_type": "class",
                    "symbol_name": class_name,
                    "class_name": class_name,
                    "function_name": "",
                    "signature": f"class {class_name}",
                    "imports": imports_str,
                    "docstring": class_doc,
                    "code": class_code,
                    "line_start": class_start,
                    "line_end": class_end
                })

                # Methods inside class
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_name = item.name
                        method_doc = ast.get_docstring(item) or ""
                        args = [a.arg for a in item.args.args]
                        sig = f"{'async ' if isinstance(item, ast.AsyncFunctionDef) else ''}def {method_name}({', '.join(args)})"
                        
                        m_start = item.lineno
                        m_end = getattr(item, "end_lineno", m_start + len(item.body))
                        m_code = get_source_segment(m_start, min(m_end, len(lines)))

                        symbols.append({
                            "repository": repository_name,
                            "file_path": str(file_path.name),
                            "language": "python",
                            "symbol_type": "method",
                            "symbol_name": f"{class_name}.{method_name}",
                            "class_name": class_name,
                            "function_name": method_name,
                            "signature": sig,
                            "imports": imports_str,
                            "docstring": method_doc,
                            "code": m_code,
                            "line_start": m_start,
                            "line_end": m_end
                        })

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name
                func_doc = ast.get_docstring(node) or ""
                args = [a.arg for a in node.args.args]
                sig = f"{'async ' if isinstance(node, ast.AsyncFunctionDef) else ''}def {func_name}({', '.join(args)})"

                f_start = node.lineno
                f_end = getattr(node, "end_lineno", f_start + len(node.body))
                f_code = get_source_segment(f_start, min(f_end, len(lines)))

                symbols.append({
                    "repository": repository_name,
                    "file_path": str(file_path.name),
                    "language": "python",
                    "symbol_type": "function",
                    "symbol_name": func_name,
                    "class_name": "",
                    "function_name": func_name,
                    "signature": sig,
                    "imports": imports_str,
                    "docstring": func_doc,
                    "code": f_code,
                    "line_start": f_start,
                    "line_end": f_end
                })

        if not symbols:
            # Entire file fallback
            symbols.append({
                "repository": repository_name,
                "file_path": str(file_path.name),
                "language": "python",
                "symbol_type": "module",
                "symbol_name": file_path.stem,
                "class_name": "",
                "function_name": "",
                "signature": f"module {file_path.stem}",
                "imports": imports_str,
                "docstring": "",
                "code": code_text[:2000],
                "line_start": 1,
                "line_end": len(lines)
            })

        return symbols

    def parse_generic_code(self, file_path: Path, repository_name: str) -> List[Dict[str, Any]]:
        code_text = file_path.read_text(encoding="utf-8", errors="replace")
        lines = code_text.splitlines()
        lang = file_path.suffix.lstrip(".") or "text"

        symbols = []
        # Regex for generic function or class definitions
        pattern = re.compile(r'^\s*(?:export\s+)?(?:async\s+)?(function|class|def|type|interface|func|fn)\s+([a-zA-Z0-9_]+)', re.MULTILINE)
        
        matches = list(pattern.finditer(code_text))
        if matches:
            for i, m in enumerate(matches):
                sym_type = m.group(1)
                sym_name = m.group(2)
                start_pos = m.start()
                end_pos = matches[i+1].start() if i+1 < len(matches) else len(code_text)
                snippet = code_text[start_pos:end_pos].strip()

                symbols.append({
                    "repository": repository_name,
                    "file_path": str(file_path.name),
                    "language": lang,
                    "symbol_type": sym_type,
                    "symbol_name": sym_name,
                    "class_name": sym_name if sym_type == "class" else "",
                    "function_name": sym_name if sym_type in ["function", "func", "fn", "def"] else "",
                    "signature": snippet.splitlines()[0] if snippet else sym_name,
                    "imports": "",
                    "docstring": "",
                    "code": snippet[:1500],
                    "line_start": code_text[:start_pos].count("\n") + 1,
                    "line_end": code_text[:end_pos].count("\n") + 1
                })
        else:
            symbols.append({
                "repository": repository_name,
                "file_path": str(file_path.name),
                "language": lang,
                "symbol_type": "file",
                "symbol_name": file_path.name,
                "class_name": "",
                "function_name": "",
                "signature": file_path.name,
                "imports": "",
                "docstring": "",
                "code": code_text[:2000],
                "line_start": 1,
                "line_end": len(lines)
            })

        return symbols


code_parser = CodeParser()
