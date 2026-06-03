from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from .config import Config

class TextChunker:
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or Config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or Config.CHUNK_OVERLAP
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
        )
    
    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        chunks = self.text_splitter.split_text(text)
        chunked_docs = []
        for idx, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata["chunk_id"] = idx
            chunked_docs.append({"text": chunk, "metadata": chunk_metadata})
        return chunked_docs
    
    def chunk_documents(self, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        all_chunks = []
        for doc in docs:
            chunks = self.chunk_text(doc["text"], doc.get("metadata"))
            all_chunks.extend(chunks)
        return all_chunks
