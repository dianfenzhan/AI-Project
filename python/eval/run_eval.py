"""离线评测脚本：定期评估召回率、精确率、重排效果与生成质量。

两类指标：
1) 检索指标（不依赖额外 LLM，便宜稳定）：
   - recall@k：标注关键词是否被召回命中
   - precision@k：Top-K 命中关键词的比例
   - 重排前后命中对比（rerank 是否把相关内容排得更靠前）
2) 生成质量指标（Ragas，需要 LLM，会消耗已配置模型的 token）：
   - faithfulness / answer_relevancy / context_precision / context_recall
   - Ragas 复用项目里已配置的大模型 key，不需要单独的 Ragas key。

用法：
    cd python
    source .venv/bin/activate
    python -m eval.run_eval                # 只跑检索指标
    python -m eval.run_eval --with-ragas   # 额外跑 Ragas 生成质量评测

前置：需要 Milvus / Elasticsearch 已启动，且评测集对应的 collection 已经上传过文档。
"""
import argparse
import json
import os
from pathlib import Path
from typing import List, Dict, Any

from RAG import VectorStore, RetrievalEngine, RerankService, Config


def load_dataset(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _hit_keywords(text: str, keywords: List[str]) -> int:
    text_lower = (text or "").lower()
    return sum(1 for kw in keywords if kw.lower() in text_lower)


def evaluate_retrieval(dataset: Dict[str, Any], top_k: int = None) -> Dict[str, Any]:
    """用标注关键词近似评估 recall@k / precision@k，以及重排带来的提升。"""
    top_k = top_k or Config.TOP_K
    vector_store = VectorStore()
    retrieval_engine = RetrievalEngine(vector_store)
    rerank_service = RerankService()

    collection_name = dataset.get("collection_name", "default")
    tenant_id = dataset.get("tenant_id", "default")

    per_sample = []
    recall_sum = precision_sum = rerank_gain_sum = 0.0
    n = 0

    for sample in dataset["samples"]:
        query = sample["query"]
        keywords = sample.get("relevant_keywords", [])
        if not keywords:
            continue

        fused = retrieval_engine.hybrid_search(query, collection_name, tenant_id)
        reranked = rerank_service.rerank(query, fused, top_k=top_k) if fused else []

        topk_docs = reranked[:top_k]
        # 命中过的关键词集合（用于 recall）
        hit_keywords = set()
        hit_doc_count = 0
        for doc in topk_docs:
            hits = _hit_keywords(doc.get("text", ""), keywords)
            if hits > 0:
                hit_doc_count += 1
            for kw in keywords:
                if kw.lower() in (doc.get("text", "") or "").lower():
                    hit_keywords.add(kw.lower())

        recall = len(hit_keywords) / len(keywords) if keywords else 0.0
        precision = hit_doc_count / len(topk_docs) if topk_docs else 0.0

        # 重排增益：比较融合原序 Top-K vs 重排 Top-K 的命中文档数
        fused_topk = fused[:top_k]
        fused_hit = sum(1 for d in fused_topk if _hit_keywords(d.get("text", ""), keywords) > 0)
        rerank_gain = hit_doc_count - fused_hit

        recall_sum += recall
        precision_sum += precision
        rerank_gain_sum += rerank_gain
        n += 1

        per_sample.append({
            "id": sample.get("id"),
            "query": query,
            "recall@k": round(recall, 3),
            "precision@k": round(precision, 3),
            "rerank_gain": rerank_gain,
            "retrieved": len(topk_docs),
        })

    summary = {
        "samples": n,
        "avg_recall@k": round(recall_sum / n, 3) if n else None,
        "avg_precision@k": round(precision_sum / n, 3) if n else None,
        "avg_rerank_gain": round(rerank_gain_sum / n, 3) if n else None,
        "top_k": top_k,
    }
    return {"summary": summary, "per_sample": per_sample}


def evaluate_with_ragas(dataset: Dict[str, Any], top_k: int = None) -> Dict[str, Any]:
    """用 Ragas 评估生成质量。需要安装 ragas / datasets，且配置了可用的 LLM。"""
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
    except ImportError:
        return {"error": "未安装 ragas / datasets，跳过。安装：pip install ragas datasets"}

    top_k = top_k or Config.TOP_K
    vector_store = VectorStore()
    retrieval_engine = RetrievalEngine(vector_store)
    rerank_service = RerankService()

    collection_name = dataset.get("collection_name", "default")
    tenant_id = dataset.get("tenant_id", "default")

    questions, contexts, answers, ground_truths = [], [], [], []
    for sample in dataset["samples"]:
        query = sample["query"]
        fused = retrieval_engine.hybrid_search(query, collection_name, tenant_id)
        reranked = rerank_service.rerank(query, fused, top_k=top_k) if fused else []
        ctx = [d.get("text", "") for d in reranked[:top_k]]

        questions.append(query)
        contexts.append(ctx or ["(no context retrieved)"])
        # 这里用 ground_truth 近似 answer；真实场景应接入生成结果
        answers.append(sample.get("ground_truth", ""))
        ground_truths.append(sample.get("ground_truth", ""))

    ds = Dataset.from_dict({
        "question": questions,
        "contexts": contexts,
        "answer": answers,
        "ground_truth": ground_truths,
    })

    try:
        result = evaluate(
            ds,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        )
        return {"ragas": str(result)}
    except Exception as exc:
        return {"error": f"Ragas 评测失败（通常是 LLM/网络问题）：{exc}"}


def main():
    parser = argparse.ArgumentParser(description="RAG 离线评测")
    parser.add_argument("--dataset", default=str(Path(__file__).parent / "dataset.json"))
    parser.add_argument("--with-ragas", action="store_true", help="额外跑 Ragas 生成质量评测")
    parser.add_argument("--top-k", type=int, default=None)
    args = parser.parse_args()

    dataset = load_dataset(args.dataset)

    print("=== 检索指标 ===")
    retrieval_report = evaluate_retrieval(dataset, args.top_k)
    print(json.dumps(retrieval_report, ensure_ascii=False, indent=2))

    if args.with_ragas:
        print("\n=== 生成质量（Ragas）===")
        ragas_report = evaluate_with_ragas(dataset, args.top_k)
        print(json.dumps(ragas_report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
