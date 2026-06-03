from typing import List, Dict, Any
from .config import Config
from .vector_store import VectorStore
from .embedding import EmbeddingService


class RetrievalEngine:
    """双路召回：Milvus 向量检索 + Elasticsearch 全文检索，合并去重后交给重排。"""

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.embedding_service = vector_store.embedding_service
        self.recall_top_k = Config.RECALL_TOP_K

    def hybrid_search(self, query: str, collection_name: str, tenant_id: str = "default") -> List[Dict[str, Any]]:
        self.vector_store.load_collection(collection_name, tenant_id)

        query_embedding = self.embedding_service.embed_text(query)

        milvus_results = self._search_milvus(query_embedding)
        es_results = self._search_es(query)

        return self._merge_results(milvus_results, es_results)

    def _search_milvus(self, query_embedding: List[float]) -> List[Dict[str, Any]]:
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
        results = self.vector_store.milvus_collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=self.recall_top_k,
            output_fields=["text", "metadata"],
        )

        docs = []
        for hit in results[0]:
            docs.append({
                "text": hit.entity.get("text"),
                "metadata": hit.entity.get("metadata"),
                "score": float(hit.score),
                "source": "milvus",
            })
        return docs

    def _search_es(self, query: str) -> List[Dict[str, Any]]:
        results = self.vector_store.es_client.search(
            index=self.vector_store.es_index,
            query={"match": {"text": query}},
            size=self.recall_top_k,
        )

        docs = []
        for hit in results["hits"]["hits"]:
            docs.append({
                "text": hit["_source"]["text"],
                "metadata": hit["_source"].get("metadata", {}),
                "score": float(hit["_score"]),
                "source": "elasticsearch",
            })
        return docs

    def _merge_results(self, milvus_docs: List[Dict], es_docs: List[Dict]) -> List[Dict]:
        # 两路分数量纲不同，这里只做去重合并，真正的排序交给后续 rerank
        seen_texts = set()
        combined = []
        for doc in milvus_docs + es_docs:
            text = doc["text"]
            if text and text not in seen_texts:
                seen_texts.add(text)
                combined.append(doc)
        return combined
