import os
from pathlib import Path
from typing import List, Dict, Any
from pypdf import PdfReader
from docx import Document

class DocumentProcessor:
    SUPPORTED_FORMATS = {".pdf", ".md", ".txt", ".docx"}
    
    @staticmethod
    def load_document(file_path: str) -> str:
        file_path_obj = Path(file_path)
        ext = file_path_obj.suffix.lower()
        
        if ext not in DocumentProcessor.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported file format: {ext}")
        
        if ext == ".pdf":
            return DocumentProcessor._load_pdf(file_path_obj)
        elif ext == ".docx":
            return DocumentProcessor._load_docx(file_path_obj)
        else:
            return DocumentProcessor._load_text(file_path_obj)
    
    @staticmethod
    def _load_pdf(file_path: Path) -> str:
        reader = PdfReader(str(file_path))
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text())
        return "\n\n".join(text_parts)
    
    @staticmethod
    def _load_docx(file_path: Path) -> str:
        doc = Document(str(file_path))
        text_parts = []
        for para in doc.paragraphs:
            text_parts.append(para.text)
        return "\n\n".join(text_parts)
    
    @staticmethod
    def _load_text(file_path: Path) -> str:
        return file_path.read_text(encoding="utf-8")
    
    @staticmethod
    def split_by_type(text: str, file_type: str) -> List[Dict[str, Any]]:
        doc_list = [{"text": text, "metadata": {"file_type": file_type}}]
        return doc_list
