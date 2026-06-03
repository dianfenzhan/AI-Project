from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
from .config import Config

class EmbeddingService:
    def __init__(self, model_name: str = None):
        self.model_name = model_name or Config.EMBEDDING_MODEL
        self.model = SentenceTransformer(self.model_name)
    
    def embed_text(self, text: str) -> List[float]:
        embedding = self.model.encode(text)
        return embedding.tolist()
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts)
        return embeddings.tolist()
