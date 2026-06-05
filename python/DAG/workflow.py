"""SEO 文章生成工作流（LangGraph 实现）。

阶段一的 DAG：
    rewrite_query -> retrieve_rag -> search_serp -> generate_titles -[中断:等用户选标题]->
    generate_outlines -[中断:等用户选大纲]-> generate_article -> quality_check -> END

通过 LangGraph 的 checkpointer + interrupt_before 实现真正的「人机交互」：
图会在生成标题后暂停，等前端把用户选择的标题写回 state 再继续；生成大纲后再次暂停。
每个会话用 thread_id 区分，RAG/SERP 只在第一步执行一次，后续步骤复用上下文。
"""
from pathlib import Path
from typing import Dict, Any, TypedDict, List

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .llm_service import LLMService
from .serp_search import SerpSearch
from .config import Config
from RAG import RetrievalEngine, VectorStore, RerankService


class SEOState(TypedDict, total=False):
    topic: str
    keywords: str
    tenant_id: str
    collection_name: str
    llm_provider: str
    rewritten_queries: List[str]
    rag_docs: List[Dict]
    serp_results: List[Dict]
    titles: List[str]
    selected_title: str
    outlines: List[str]
    selected_outline: str
    article: str
    citations: List[Dict]
    quality_report: Dict[str, Any]


# 图中需要暂停等待用户输入的节点
_INTERRUPT_NODES = ["generate_outlines", "generate_article"]


class SEOWorkflow:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.rerank_service = RerankService()
        self.retrieval_engine = RetrievalEngine(vector_store)
        self.serp_search = SerpSearch()
        self.article_template = self._load_template()
        # 单进程内存级 checkpointer：保存每个 thread_id 的中间状态，支持多次恢复
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()

    @staticmethod
    def _load_template() -> str:
        path = Path(Config.ARTICLE_TEMPLATE_PATH)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _build_graph(self):
        graph = StateGraph(SEOState)
        graph.add_node("rewrite_query", self._rewrite_query)
        graph.add_node("retrieve_rag", self._retrieve_rag)
        graph.add_node("search_serp", self._search_serp)
        graph.add_node("generate_titles", self._generate_titles)
        graph.add_node("generate_outlines", self._generate_outlines)
        graph.add_node("generate_article", self._generate_article)
        graph.add_node("quality_check", self._quality_check)

        graph.set_entry_point("rewrite_query")
        graph.add_edge("rewrite_query", "retrieve_rag")
        graph.add_edge("retrieve_rag", "search_serp")
        graph.add_edge("search_serp", "generate_titles")
        graph.add_edge("generate_titles", "generate_outlines")
        graph.add_edge("generate_outlines", "generate_article")
        graph.add_edge("generate_article", "quality_check")
        graph.add_edge("quality_check", END)

        return graph.compile(
            checkpointer=self.checkpointer,
            interrupt_before=_INTERRUPT_NODES,
        )

    # ---------------- 节点实现 ----------------

    def _rewrite_query(self, state: SEOState) -> Dict[str, Any]:
        base_query = self._base_query(state)
        llm = LLMService(state["llm_provider"], temperature=0.2)
        prompt = f"""你是 RAG 检索 query 改写专家。请基于用户主题和关键词生成 3-5 个中文检索 query，用于从企业知识库中召回 SEO 文章素材。
要求：
1. 覆盖主题背景、用户痛点、解决方案、FAQ 等不同角度。
2. 保留核心关键词，不要生成无关 query。
3. 只返回 JSON，格式：{{"queries": ["query1", "query2", "query3"]}}

主题：{state['topic']}
关键词：{state.get('keywords', '')}
原始 query：{base_query}
"""
        try:
            data = llm.generate_json(prompt)
            queries = data.get("queries") if isinstance(data, dict) else None
        except Exception:
            queries = None

        normalized = [base_query]
        if isinstance(queries, list):
            for query in queries:
                if isinstance(query, str):
                    value = query.strip()
                    if value and value not in normalized:
                        normalized.append(value)

        return {"rewritten_queries": normalized[:5]}

    def _retrieve_rag(self, state: SEOState) -> Dict[str, Any]:
        base_query = self._base_query(state)
        queries = state.get("rewritten_queries") or [base_query]
        docs_by_text = {}
        for query in queries:
            docs = self.retrieval_engine.hybrid_search(
                query, state["collection_name"], state["tenant_id"]
            )
            for doc in docs:
                text = doc.get("text")
                if not text:
                    continue
                current = docs_by_text.get(text)
                if current is None or doc.get("score", 0) > current.get("score", 0):
                    enriched = doc.copy()
                    metadata = dict(enriched.get("metadata") or {})
                    metadata["matched_query"] = query
                    enriched["metadata"] = metadata
                    docs_by_text[text] = enriched

        reranked = self.rerank_service.rerank(base_query, list(docs_by_text.values()))
        return {"rag_docs": reranked}

    def _search_serp(self, state: SEOState) -> Dict[str, Any]:
        results = self.serp_search.search_and_fetch(state["topic"])
        return {"serp_results": results}

    def _generate_titles(self, state: SEOState) -> Dict[str, Any]:
        llm = LLMService(state["llm_provider"])
        context = self._build_context(state)
        prompt = f"""你是资深 SEO 专家。基于下面的「参考资料」，为主题「{state['topic']}」生成 5 个吸引人、利于搜索排名的中文标题。
要求：自然融入关键词「{state['keywords']}」；标题之间角度不同；不要编号。
只返回 JSON，格式：{{"titles": ["标题1", "标题2", "标题3", "标题4", "标题5"]}}

参考资料：
{context}
"""
        data = llm.generate_json(prompt)
        titles = (data or {}).get("titles") if isinstance(data, dict) else None
        if not titles:
            titles = [f"{state['topic']}（自动生成标题）"]
        return {"titles": titles[:5]}

    def _generate_outlines(self, state: SEOState) -> Dict[str, Any]:
        title = state.get("selected_title") or (state["titles"][0] if state.get("titles") else state["topic"])
        llm = LLMService(state["llm_provider"])
        context = self._build_context(state)
        prompt = f"""你是资深 SEO 专家。为文章标题「{title}」设计 3 套不同结构的中文大纲。
要求：每套大纲用 markdown 列表（一级标题用 #，小节用 -）；3 套侧重点要有差异；覆盖关键词「{state['keywords']}」。
只返回 JSON，格式：{{"outlines": ["大纲1的markdown文本", "大纲2的markdown文本", "大纲3的markdown文本"]}}

参考资料：
{context}
"""
        data = llm.generate_json(prompt)
        outlines = (data or {}).get("outlines") if isinstance(data, dict) else None
        if not outlines:
            outlines = [f"# {title}\n- 引言\n- 正文\n- 结论"]
        return {"outlines": outlines[:3]}

    def _generate_article(self, state: SEOState) -> Dict[str, Any]:
        title = state.get("selected_title") or (state["titles"][0] if state.get("titles") else state["topic"])
        outline = state.get("selected_outline") or (state["outlines"][0] if state.get("outlines") else "")
        llm = LLMService(state["llm_provider"])

        knowledge_base = self._format_rag(state)
        web_info = self._format_serp(state)
        citations = self._build_citations(state)

        prompt = f"""language: 中文
title: {title}
keyword: {state['keywords']}
topic: {state['topic']}
tone: 专业、信息丰富
audience: 目标潜在客户
grounding_rules:
- 优先依据 knowledgeBase，其次依据 web_info。
- 如果 knowledgeBase 为（无），不要编造企业内部资料，只能基于 web_info 或通用表达。
- 涉及事实、数据、定义、方案时，尽量在句末标注来源编号，例如 [KB1]、[WEB2]。
- 如果参考资料不足，请在文章中明确说明信息边界，不要把不确定内容写成事实。
outline:
{outline}
web_info:
{web_info}
knowledgeBase:
{knowledge_base}
length: 不少于 1000 字
"""
        # 文章模版作为 system 指令，约束输出格式与写作规则
        system = self.article_template or "你是资深 SEO 专家，请根据大纲撰写文章，输出 markdown。"
        article = llm.generate(prompt, system=system)
        return {"article": article, "citations": citations}

    def _quality_check(self, state: SEOState) -> Dict[str, Any]:
        article = state.get("article", "")
        if not article:
            return {"quality_report": self._fallback_quality_report("文章为空")}

        llm = LLMService(state["llm_provider"], temperature=0.0)
        context = self._build_context(state)
        prompt = f"""你是 RAG 文章质量评估器。请基于参考资料评估文章质量。
只返回 JSON，格式：
{{
  "faithfulness": 0-100,
  "relevance": 0-100,
  "structure": 0-100,
  "citation_coverage": 0-100,
  "overall": 0-100,
  "risks": ["风险1", "风险2"],
  "suggestions": ["建议1", "建议2"]
}}

评分标准：
- faithfulness：文章中的事实是否能被参考资料支持。
- relevance：是否围绕主题和关键词。
- structure：是否符合 SEO 文章结构。
- citation_coverage：关键事实是否有 [KBx]/[WEBx] 来源标注。

主题：{state['topic']}
关键词：{state['keywords']}

参考资料：
{context}

文章：
{article[:6000]}
"""
        try:
            report = llm.generate_json(prompt)
            if isinstance(report, dict):
                return {"quality_report": report}
        except Exception as exc:
            return {"quality_report": self._fallback_quality_report(str(exc))}

        return {"quality_report": self._fallback_quality_report("质量评估 JSON 解析失败")}

    # ---------------- 上下文构造 ----------------

    @staticmethod
    def _base_query(state: SEOState) -> str:
        return f"{state['topic']} {state.get('keywords', '')}".strip()

    def _format_rag(self, state: SEOState, limit: int = 8) -> str:
        docs = state.get("rag_docs") or []
        parts = []
        for idx, doc in enumerate(docs[:limit], start=1):
            metadata = doc.get("metadata") or {}
            filename = metadata.get("filename", "unknown")
            chunk_id = metadata.get("chunk_id", "unknown")
            matched_query = metadata.get("matched_query", "")
            parts.append(
                f"[KB{idx}] filename={filename}, chunk_id={chunk_id}, matched_query={matched_query}\n"
                f"{doc.get('text', '')}"
            )
        return "\n\n".join(parts) or "（无）"

    def _format_serp(self, state: SEOState, limit: int = 5) -> str:
        results = state.get("serp_results") or []
        parts = []
        for idx, r in enumerate(results[:limit], start=1):
            snippet = r.get("content") or r.get("snippet") or ""
            parts.append(f"[WEB{idx}] {r.get('title', '')} ({r.get('link', '')})\n{snippet[:800]}")
        return "\n".join(parts) or "（无）"

    def _build_context(self, state: SEOState) -> str:
        return f"## 知识库内容：\n{self._format_rag(state)}\n\n## 网络搜索内容：\n{self._format_serp(state)}"

    def _build_citations(self, state: SEOState) -> List[Dict[str, Any]]:
        citations = []
        for idx, doc in enumerate((state.get("rag_docs") or [])[:8], start=1):
            metadata = doc.get("metadata") or {}
            citations.append({
                "id": f"KB{idx}",
                "type": "knowledge_base",
                "filename": metadata.get("filename"),
                "chunk_id": metadata.get("chunk_id"),
                "matched_query": metadata.get("matched_query"),
                "source": doc.get("source"),
                "score": doc.get("rerank_score", doc.get("score")),
                "text_preview": (doc.get("text") or "")[:300],
            })
        for idx, result in enumerate((state.get("serp_results") or [])[:5], start=1):
            citations.append({
                "id": f"WEB{idx}",
                "type": "web",
                "title": result.get("title"),
                "link": result.get("link"),
                "text_preview": (result.get("content") or result.get("snippet") or "")[:300],
            })
        return citations

    @staticmethod
    def _fallback_quality_report(reason: str) -> Dict[str, Any]:
        return {
            "faithfulness": None,
            "relevance": None,
            "structure": None,
            "citation_coverage": None,
            "overall": None,
            "risks": [reason],
            "suggestions": ["检查 LLM 服务是否可用，或稍后重新生成质量评估。"],
        }

    # ---------------- 对外的分步执行接口 ----------------

    def _config(self, thread_id: str) -> Dict[str, Any]:
        return {"configurable": {"thread_id": thread_id}}

    def start(self, initial_state: SEOState, thread_id: str) -> List[str]:
        """第一步：执行 RAG + SERP + 生成标题，在生成大纲前暂停。返回 5 个标题。"""
        config = self._config(thread_id)
        self.graph.invoke(initial_state, config)
        return self.graph.get_state(config).values.get("titles", [])

    def choose_title(self, thread_id: str, selected_title: str) -> List[str]:
        """第二步：写回用户选择的标题，恢复执行生成 3 套大纲，在生成文章前暂停。"""
        config = self._config(thread_id)
        self.graph.update_state(config, {"selected_title": selected_title})
        self.graph.invoke(None, config)
        return self.graph.get_state(config).values.get("outlines", [])

    def choose_outline(self, thread_id: str, selected_outline: str) -> Dict[str, Any]:
        """第三步：写回用户选择的大纲，恢复执行生成文章，并返回文章、引用和质量评估。"""
        config = self._config(thread_id)
        self.graph.update_state(config, {"selected_outline": selected_outline})
        self.graph.invoke(None, config)
        values = self.graph.get_state(config).values
        return {
            "article": values.get("article", ""),
            "quality_report": values.get("quality_report", {}),
            "citations": values.get("citations", []),
            "rewritten_queries": values.get("rewritten_queries", []),
        }
