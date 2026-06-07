import uuid
from typing import List, Dict, Any, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter
from .config import Config


class TextChunker:
    """文本切块。

    一期（当前默认）：用 tiktoken 控制 token 数，而不是固定字符数。
    - chunk_size / chunk_overlap 单位是 token，更贴近 LLM 真实上下文消耗。
    - 仍用 RecursiveCharacterTextSplitter 的递归分隔（段落 -> 换行 -> 句子 -> 词），
      但长度度量换成 tiktoken 编码后的 token 数。

    二期（预留接口 structure_aware_chunk）：按标题 / 段落 / Markdown 层级做结构化切块，
    并在 metadata 中记录 doc_id / section_title / page_number / chunk_id，便于答案溯源。
    """

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or Config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or Config.CHUNK_OVERLAP
        # 英文为主，分隔符以英文标点优先，兼容中文标点
        self.separators = ["\n\n", "\n", ". ", "? ", "! ", "。", "！", "？", " ", ""]
        self.text_splitter = self._build_splitter()

    def _build_splitter(self) -> RecursiveCharacterTextSplitter:
        """优先用 tiktoken 控制 token 数；tiktoken 不可用时优雅降级为字符长度。"""
        try:
            return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                encoding_name=Config.TIKTOKEN_ENCODING,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=self.separators,
            )
        except Exception:
            # 降级：按字符长度切，保证服务可启动
            return RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=self.separators,
            )

    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        base_metadata = dict(metadata or {})
        # 为同一篇文档生成稳定的 doc_id，便于后续溯源与去重
        doc_id = base_metadata.get("doc_id") or uuid.uuid4().hex
        base_metadata["doc_id"] = doc_id

        chunks = self.text_splitter.split_text(text)
        chunked_docs = []
        for idx, chunk in enumerate(chunks):
            chunk_metadata = dict(base_metadata)
            chunk_metadata["chunk_id"] = idx
            chunked_docs.append({"text": chunk, "metadata": chunk_metadata})
        return chunked_docs

    def chunk_documents(self, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        all_chunks = []
        for doc in docs:
            chunks = self.chunk_text(doc["text"], doc.get("metadata"))
            all_chunks.extend(chunks)
        return all_chunks

    # ---------------- 二期：结构化切块（预留接口） ----------------

    def structure_aware_chunk(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
        sections: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """二期结构化切块（预留）。

        规划：
        - 按 Markdown 标题层级 / 段落结构切块，而不是只按字符或 token。
        - 针对 SEO 文档，可按「标题、问题、解决方案、结论」做语义切块。
        - metadata 记录 doc_id / section_title / page_number / chunk_id，提升答案溯源能力。

        当前未启用：若传入 sections（[{title, text, page_number}, ...]）则按 section 切，
        否则回退到一期的 token 切块，保证调用方不报错。
        """
        if not sections:
            return self.chunk_text(text, metadata)

        base_metadata = dict(metadata or {})
        doc_id = base_metadata.get("doc_id") or uuid.uuid4().hex
        base_metadata["doc_id"] = doc_id

        all_chunks: List[Dict[str, Any]] = []
        chunk_id = 0
        for section in sections:
            section_meta = dict(base_metadata)
            section_meta["section_title"] = section.get("title")
            section_meta["page_number"] = section.get("page_number")
            for piece in self.text_splitter.split_text(section.get("text", "")):
                piece_meta = dict(section_meta)
                piece_meta["chunk_id"] = chunk_id
                all_chunks.append({"text": piece, "metadata": piece_meta})
                chunk_id += 1
        return all_chunks
