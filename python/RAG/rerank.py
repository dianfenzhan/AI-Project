from typing import List, Dict, Any
from flashrank import Ranker, RerankRequest
from .config import Config


class RerankService:
    """基于 FlashRank 的重排序服务。

    双路召回（Milvus 向量 + ES 全文）得到的候选集合分数不在同一量纲，
    无法直接比较，因此统一交给 cross-encoder 重排，输出最终 Top-K。
    """

    def __init__(self):
        # 多语言 cross-encoder（默认 ms-marco-MultiBERT-L-12），中英文 query-doc 均可重排
        self.ranker = Ranker(model_name=Config.RERANK_MODEL)

    def rerank(self, query: str, docs: List[Dict[str, Any]], top_k: int = None) -> List[Dict[str, Any]]:
        top_k = top_k or Config.TOP_K

        if not docs:
            return []

        # FlashRank 0.2.x 的正确用法：传入 RerankRequest，passages 为带 id/text 的字典列表
        passages = [{"id": idx, "text": doc["text"]} for idx, doc in enumerate(docs)]
        rerank_request = RerankRequest(query=query, passages=passages)
        results = self.ranker.rerank(rerank_request)

        reranked_docs = []
        for res in results[:top_k]:
            idx = res["id"]
            doc = docs[idx].copy()
            doc["rerank_score"] = float(res["score"])
            reranked_docs.append(doc)

        return reranked_docs
