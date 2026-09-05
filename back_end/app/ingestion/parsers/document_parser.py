import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import pypdf
import docx

class DocumentParser:
    """
    Structure-aware parser for unstructured documents (PDF, DOCX, Markdown, HTML, TXT).
    Extracts heading hierarchy and forms logical parent sections.
    """
    def parse(self, file_path: Path, category: str) -> List[Dict[str, Any]]:
        if category == "markdown":
            return self.parse_markdown(file_path)
        elif category == "html":
            return self.parse_html(file_path)
        elif category == "docx":
            return self.parse_docx(file_path)
        elif category == "pdf":
            return self.parse_pdf(file_path)
        else:
            return self.parse_text(file_path)

    def parse_markdown(self, file_path: Path) -> List[Dict[str, Any]]:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        
        sections: List[Dict[str, Any]] = []
        heading_stack: List[str] = [file_path.stem]
        current_content: List[str] = []
        
        for line in lines:
            heading_match = re.match(r'^(#{1,6})\s+(.*)$', line)
            if heading_match:
                # Flush previous section
                if current_content:
                    sections.append({
                        "heading_path": " > ".join(heading_stack),
                        "content": "\n".join(current_content).strip(),
                        "section_order": len(sections)
                    })
                    current_content = []
                
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                
                # Adjust stack to current level
                heading_stack = heading_stack[:1] + heading_stack[1:level]
                if len(heading_stack) < level:
                    heading_stack.extend([""] * (level - len(heading_stack)))
                if level < len(heading_stack):
                    heading_stack[level] = title
                else:
                    heading_stack.append(title)
                heading_stack = [h for h in heading_stack if h]
            else:
                current_content.append(line)

        if current_content:
            sections.append({
                "heading_path": " > ".join(heading_stack),
                "content": "\n".join(current_content).strip(),
                "section_order": len(sections)
            })

        return [s for s in sections if s["content"]]

    def parse_html(self, file_path: Path) -> List[Dict[str, Any]]:
        html_content = file_path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove script and style elements
        for s in soup(["script", "style", "nav", "footer"]):
            s.decompose()

        sections: List[Dict[str, Any]] = []
        heading_stack = [file_path.stem]
        current_content: List[str] = []

        for elem in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "pre", "table"]):
            if elem.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                if current_content:
                    sections.append({
                        "heading_path": " > ".join(heading_stack),
                        "content": "\n".join(current_content).strip(),
                        "section_order": len(sections)
                    })
                    current_content = []
                level = int(elem.name[1])
                title = elem.get_text().strip()
                heading_stack = heading_stack[:level]
                heading_stack.append(title)
            else:
                text = elem.get_text().strip()
                if text:
                    current_content.append(text)

        if current_content:
            sections.append({
                "heading_path": " > ".join(heading_stack),
                "content": "\n".join(current_content).strip(),
                "section_order": len(sections)
            })

        return [s for s in sections if s["content"]]

    def parse_docx(self, file_path: Path) -> List[Dict[str, Any]]:
        doc = docx.Document(str(file_path))
        sections: List[Dict[str, Any]] = []
        heading_stack = [file_path.stem]
        current_content: List[str] = []

        for p in doc.paragraphs:
            style_name = p.style.name.lower() if p.style else ""
            if "heading" in style_name:
                if current_content:
                    sections.append({
                        "heading_path": " > ".join(heading_stack),
                        "content": "\n".join(current_content).strip(),
                        "section_order": len(sections)
                    })
                    current_content = []
                heading_stack = [file_path.stem, p.text.strip()]
            else:
                if p.text.strip():
                    current_content.append(p.text.strip())

        if current_content:
            sections.append({
                "heading_path": " > ".join(heading_stack),
                "content": "\n".join(current_content).strip(),
                "section_order": len(sections)
            })

        return [s for s in sections if s["content"]]

    def parse_pdf(self, file_path: Path) -> List[Dict[str, Any]]:
        reader = pypdf.PdfReader(str(file_path))
        sections: List[Dict[str, Any]] = []
        current_heading = file_path.stem
        
        for idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            lines = page_text.splitlines()
            page_content: List[str] = []

            for line in lines:
                clean_line = line.strip()
                if not clean_line:
                    continue
                # Heading heuristic: uppercase or short line followed by paragraphs
                if len(clean_line) < 60 and (clean_line.isupper() or re.match(r'^\d+(\.\d+)*\s+[A-Z]', clean_line)):
                    if page_content:
                        sections.append({
                            "heading_path": f"{file_path.stem} > {current_heading}",
                            "content": "\n".join(page_content).strip(),
                            "section_order": len(sections),
                            "page_number": idx + 1
                        })
                        page_content = []
                    current_heading = clean_line
                else:
                    page_content.append(clean_line)

            if page_content:
                sections.append({
                    "heading_path": f"{file_path.stem} > {current_heading}",
                    "content": "\n".join(page_content).strip(),
                    "section_order": len(sections),
                    "page_number": idx + 1
                })

        return [s for s in sections if s["content"]]

    def parse_text(self, file_path: Path) -> List[Dict[str, Any]]:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        
        sections = []
        for i, p in enumerate(paragraphs):
            sections.append({
                "heading_path": f"{file_path.stem} > Section {i+1}",
                "content": p,
                "section_order": i
            })
        return sections


document_parser = DocumentParser()
