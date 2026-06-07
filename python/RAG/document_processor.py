import os
from pathlib import Path
from typing import List, Dict, Any
from pypdf import PdfReader
from docx import Document


class DocumentProcessor:
    """文档解析。

    PDF 分三类处理：
    1) 源文件 PDF（数字文本）：pypdf 直接抽取文本。
    2) 扫描件 PDF（图片型）：pypdf 抽不到文本时走 OCR（pytesseract + pdf2image）。
       OCR 需本机安装 tesseract（Mac: brew install tesseract）和 poppler，未安装时优雅降级并提示。
    3) 带表格 PDF：用 pdfplumber 抽取表格，转成 Markdown 表格，保留专业数据的行列结构。

    所有可选依赖（pdfplumber / pytesseract / pdf2image）都在函数内部 try-import，
    缺失时不影响主流程，只是对应能力降级。
    """

    SUPPORTED_FORMATS = {".pdf", ".md", ".txt", ".docx"}
    # pypdf 抽取文本长度低于该阈值，判定为扫描件，触发 OCR
    SCANNED_TEXT_THRESHOLD = 20

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

    # ---------------- PDF ----------------

    @staticmethod
    def _load_pdf(file_path: Path) -> str:
        """综合三类 PDF：文本层 +（扫描件 OCR 兜底）+ 表格层。"""
        text = DocumentProcessor._extract_pdf_text(file_path)

        # 扫描件：文本层几乎为空 -> OCR
        if len(text.strip()) < DocumentProcessor.SCANNED_TEXT_THRESHOLD:
            ocr_text = DocumentProcessor._ocr_pdf(file_path)
            if ocr_text.strip():
                text = ocr_text

        # 表格：单独抽取并转 Markdown，追加到正文后面
        tables_md = DocumentProcessor._extract_pdf_tables(file_path)
        if tables_md.strip():
            text = f"{text}\n\n## Extracted Tables\n{tables_md}"

        return text

    @staticmethod
    def _extract_pdf_text(file_path: Path) -> str:
        reader = PdfReader(str(file_path))
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        return "\n\n".join(text_parts)

    @staticmethod
    def _ocr_pdf(file_path: Path) -> str:
        """扫描件 OCR：pdf2image 渲染成图片 + pytesseract 识别。依赖缺失时降级。"""
        try:
            import pytesseract
            from pdf2image import convert_from_path
        except ImportError:
            return (
                "[OCR 跳过] 检测到疑似扫描件，但未安装 OCR 依赖。"
                "请安装：pip install pytesseract pdf2image，并安装系统 tesseract（Mac: brew install tesseract）与 poppler。"
            )

        try:
            images = convert_from_path(str(file_path))
        except Exception as exc:
            return f"[OCR 跳过] 无法渲染 PDF 为图片（可能缺少 poppler）：{exc}"

        ocr_parts = []
        for image in images:
            try:
                # 出海内容以英文为主，OCR 语言用 eng
                ocr_parts.append(pytesseract.image_to_string(image, lang="eng"))
            except Exception as exc:
                ocr_parts.append(f"[OCR 失败] {exc}")
        return "\n\n".join(ocr_parts)

    @staticmethod
    def _extract_pdf_tables(file_path: Path) -> str:
        """用 pdfplumber 抽取表格并转成 Markdown 表格。依赖缺失时降级为空串。"""
        try:
            import pdfplumber
        except ImportError:
            return ""

        md_tables = []
        try:
            with pdfplumber.open(str(file_path)) as pdf:
                for page_idx, page in enumerate(pdf.pages, start=1):
                    for table in page.extract_tables() or []:
                        rendered = DocumentProcessor._table_to_markdown(table)
                        if rendered:
                            md_tables.append(f"### Table (page {page_idx})\n{rendered}")
        except Exception as exc:
            return f"[表格抽取失败] {exc}"

        return "\n\n".join(md_tables)

    @staticmethod
    def _table_to_markdown(table: List[List[Any]]) -> str:
        rows = [
            [("" if cell is None else str(cell)).replace("\n", " ").strip() for cell in row]
            for row in table if row
        ]
        if not rows:
            return ""
        header = rows[0]
        col_count = len(header)
        lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * col_count) + " |"]
        for row in rows[1:]:
            padded = row + [""] * (col_count - len(row))
            lines.append("| " + " | ".join(padded[:col_count]) + " |")
        return "\n".join(lines)

    # ---------------- 其他格式 ----------------

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
