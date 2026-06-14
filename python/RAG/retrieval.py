from typing import List, Dict, Any
from .config import Config
from .vector_store import VectorStore
from .embedding import EmbeddingService


class RetrievalEngine:
    """双路召回 + RRF 融合 + 两级权限。

    召回来源：
    - 租户级集合（仅当前 tenant 可见）
    - 系统级集合（所有租户共享）

    每个来源都做 Milvus 向量召回 + Elasticsearch 全文召回，共最多 4 路 ranked list；
    用 RRF（Reciprocal Rank Fusion）按排名融合，输出排序更合理的候选集，再交给 rerank。

    权限控制：检索只会访问「当前租户集合」+「系统级集合」，绝不会读到其他租户的数据。
    """

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.embedding_service = vector_store.embedding_service
        self.recall_top_k = Config.RECALL_TOP_K
        self.rrf_k = Config.RRF_K

    def hybrid_search(self, query: str, collection_name: str, tenant_id: str = "default") -> List[Dict[str, Any]]:
        query_embedding = self.embedding_service.embed_text(query, is_query=True)

        # 允许访问的 scope：当前租户 + 系统级（共享）
        scopes = [
            (tenant_id, Config.SCOPE_TENANT),
            (Config.SYSTEM_TENANT_ID, Config.SCOPE_SYSTEM),
        ]

        ranked_lists: List[List[Dict[str, Any]]] = []
        for store_tenant_id, scope in scopes:
            milvus_docs = self.vector_store.search_milvus(
                query_embedding, collection_name, store_tenant_id, self.recall_top_k
            )
            es_docs = self.vector_store.search_es(
                query, collection_name, store_tenant_id, self.recall_top_k
            )
            for doc in milvus_docs + es_docs:
                doc.setdefault("metadata", {})
                if doc["metadata"] is None:
                    doc["metadata"] = {}
                doc["metadata"]["access_scope"] = scope
            if milvus_docs:
                ranked_lists.append(milvus_docs)
            if es_docs:
                ranked_lists.append(es_docs)

        return self._rrf_fuse(ranked_lists)

    def _rrf_fuse(self, ranked_lists: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Reciprocal Rank Fusion：对每个 ranked list，按 rank 累加 1/(K + rank)。

        不同检索系统的原始分数量纲不同（Milvus 余弦 vs ES BM25），直接相加不合理；
        RRF 只依赖「排名」，对量纲不敏感，是工程上常用且稳健的多路融合方法。
        """
        fused: Dict[str, Dict[str, Any]] = {}
        for ranked in ranked_lists:
            for rank, doc in enumerate(ranked, start=1):
                text = doc.get("text")
                if not text:
                    continue
                contribution = 1.0 / (self.rrf_k + rank)
                if text not in fused:
                    merged = dict(doc)
                    merged["rrf_score"] = contribution
                    merged["sources"] = [doc.get("source")]
                    fused[text] = merged
                else:
                    fused[text]["rrf_score"] += contribution
                    fused[text]["sources"].append(doc.get("source"))

        return sorted(fused.values(), key=lambda d: d["rrf_score"], reverse=True)
