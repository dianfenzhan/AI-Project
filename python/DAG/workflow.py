"""SEO 文章生成工作流（LangGraph 实现）。

DAG：
    rewrite_query -> retrieve_rag -> search_serp -> generate_titles
    -[中断:等用户选标题]-> generate_outlines
    -[中断:等用户选大纲]-> generate_article -> quality_check -> END

这条「检索 -> 生成」链路本身就是一个 DAG，用 LangGraph 编排：
- 持久化：SqliteSaver 落盘 checkpoint，进程重启/崩溃后可按 thread_id 断点续跑。
- 人机交互：interrupt_before 在生成标题、大纲后暂停，等前端写回用户选择再继续。
- 重试 / 回退：节点内部对检索、重排、SERP 做降级；LLM 调用由 LLMService 做多模型降级 + 重试。
- 可观测：每次运行挂载 Langfuse callback（云端，可选），上报 prompt/模型/token/耗时/调用链。

业务为英文出海内容，所有生成 prompt 均要求英文输出，与英文文章模版保持一致。
"""
import sqlite3
from pathlib import Path
from typing import Dict, Any, TypedDict, List

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .llm_service import LLMService
from .serp_search import SerpSearch
from .config import Config
from . import observability
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
        self.checkpointer = self._build_checkpointer()
        self.graph = self._build_graph()

    @staticmethod
    def _load_template() -> str:
        path = Path(Config.ARTICLE_TEMPLATE_PATH)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _build_checkpointer(self):
        """优先用 SQLite 落盘 checkpoint（断点续跑）；不可用时降级为内存级。"""
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
            conn = sqlite3.connect(Config.CHECKPOINT_DB_PATH, check_same_thread=False)
            return SqliteSaver(conn)
        except Exception:
            return MemorySaver()

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
        llm = LLMService(state.get("llm_provider"), temperature=0.2)
        prompt = f"""You are a retrieval query rewriting expert for an English SEO content RAG system.
Generate 3-5 English search queries to retrieve source material from the knowledge base.
Requirements:
1. Cover different angles: topic background, user pain points, solutions, FAQs.
2. Keep the core keywords; do not produce unrelated queries.
3. Return JSON only, format: {{"queries": ["query1", "query2", "query3"]}}

Topic: {state['topic']}
Keywords: {state.get('keywords', '')}
Original query: {base_query}
"""
        try:
            data = llm.generate_json(prompt)
            queries = data.get("queries") if isinstance(data, dict) else None
        except Exception:
            queries = None

        return {"rewritten_queries": self._dedup_queries(base_query, queries)}

    @staticmethod
    def _dedup_queries(base_query: str, queries) -> List[str]:
        """对改写出的 query 做规范化去重：小写 + 去首尾空白，保留原始大小写展示。"""
        seen = set()
        result: List[str] = []
        candidates = [base_query] + (queries if isinstance(queries, list) else [])
        for q in candidates:
            if not isinstance(q, str):
                continue
            value = q.strip()
            if not value:
                continue
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return result[:5]

    def _retrieve_rag(self, state: SEOState) -> Dict[str, Any]:
        base_query = self._base_query(state)
        queries = state.get("rewritten_queries") or [base_query]

        docs_by_text: Dict[str, Dict[str, Any]] = {}
        for query in queries:
            try:
                docs = self.retrieval_engine.hybrid_search(
                    query, state["collection_name"], state["tenant_id"]
                )
            except Exception:
                # 单个 query 检索失败不应阻断整体，跳过即可（降级）
                continue
            for doc in docs:
                text = doc.get("text")
                if not text:
                    continue
                current = docs_by_text.get(text)
                score = doc.get("rrf_score", doc.get("score", 0))
                if current is None or score > current.get("rrf_score", current.get("score", 0)):
                    enriched = dict(doc)
                    metadata = dict(enriched.get("metadata") or {})
                    metadata["matched_query"] = query
                    enriched["metadata"] = metadata
                    docs_by_text[text] = enriched

        candidates = list(docs_by_text.values())

        # 重排；失败则降级为「不重排，直接按融合分取 Top-K」
        try:
            reranked = self.rerank_service.rerank(base_query, candidates)
        except Exception:
            reranked = sorted(
                candidates,
                key=lambda d: d.get("rrf_score", d.get("score", 0)),
                reverse=True,
            )[:Config.TOP_K]

        return {"rag_docs": reranked}

    def _search_serp(self, state: SEOState) -> Dict[str, Any]:
        try:
            results = self.serp_search.search_and_fetch(state["topic"])
        except Exception:
            results = []  # 外部搜索失败时降级为仅用知识库
        return {"serp_results": results}

    def _generate_titles(self, state: SEOState) -> Dict[str, Any]:
        llm = LLMService(state.get("llm_provider"))
        context = self._build_context(state)
        prompt = f"""You are a senior SEO expert. Based on the reference material below, generate 5 catchy,
search-friendly English titles for the topic "{state['topic']}".
Requirements: naturally include the keywords "{state['keywords']}"; make the titles differ in angle; no numbering.
Return JSON only, format: {{"titles": ["title1", "title2", "title3", "title4", "title5"]}}

Reference material:
{context}
"""
        data = llm.generate_json(prompt)
        titles = (data or {}).get("titles") if isinstance(data, dict) else None
        if not titles:
            titles = [f"{state['topic']} (auto-generated title)"]
        return {"titles": titles[:5]}

    def _generate_outlines(self, state: SEOState) -> Dict[str, Any]:
        title = state.get("selected_title") or (state["titles"][0] if state.get("titles") else state["topic"])
        llm = LLMService(state.get("llm_provider"))
        context = self._build_context(state)
        prompt = f"""You are a senior SEO expert. Design 3 differently-structured English outlines for the title "{title}".
Requirements: each outline uses markdown lists (top-level headings with #, sub-items with -); the 3 outlines must differ in focus; cover the keywords "{state['keywords']}".
Return JSON only, format: {{"outlines": ["outline1 markdown", "outline2 markdown", "outline3 markdown"]}}

Reference material:
{context}
"""
        data = llm.generate_json(prompt)
        outlines = (data or {}).get("outlines") if isinstance(data, dict) else None
        if not outlines:
            outlines = [f"# {title}\n- Introduction\n- Body\n- Conclusion"]
        return {"outlines": outlines[:3]}

    def _generate_article(self, state: SEOState) -> Dict[str, Any]:
        title = state.get("selected_title") or (state["titles"][0] if state.get("titles") else state["topic"])
        outline = state.get("selected_outline") or (state["outlines"][0] if state.get("outlines") else "")
        llm = LLMService(state.get("llm_provider"))

        knowledge_base = self._format_rag(state)
        web_info = self._format_serp(state)
        citations = self._build_citations(state)

        prompt = f"""language: English
title: {title}
keyword: {state['keywords']}
topic: {state['topic']}
tone: professional, informative
audience: target prospective customers
grounding_rules:
- Prefer knowledgeBase first, then web_info.
- If knowledgeBase is (none), do not fabricate internal facts; rely on web_info or general statements.
- For facts, data, definitions and solutions, cite the source id at the end of the sentence, e.g. [KB1], [WEB2].
- If the reference material is insufficient, state the information boundary explicitly; do not present uncertain content as fact.
outline:
{outline}
web_info:
{web_info}
knowledgeBase:
{knowledge_base}
length: at least 1000 words
"""
        # 文章模版作为 system 指令，约束输出格式与写作规则（模版本身为英文）
        system = self.article_template or "You are a senior SEO expert. Write the article based on the outline and output markdown."
        article = llm.generate(prompt, system=system)
        return {"article": article, "citations": citations}

    def _quality_check(self, state: SEOState) -> Dict[str, Any]:
        article = state.get("article", "")
        if not article:
            return {"quality_report": self._fallback_quality_report("Article is empty")}

        llm = LLMService(state.get("llm_provider"), temperature=0.0)
        context = self._build_context(state)
        prompt = f"""You are a RAG article quality evaluator. Evaluate the article based on the reference material.
Return JSON only, format:
{{
  "faithfulness": 0-100,
  "relevance": 0-100,
  "structure": 0-100,
  "citation_coverage": 0-100,
  "overall": 0-100,
  "risks": ["risk1", "risk2"],
  "suggestions": ["suggestion1", "suggestion2"]
}}

Scoring criteria:
- faithfulness: whether the facts are supported by the reference material.
- relevance: whether it stays on the topic and keywords.
- structure: whether it follows a good SEO article structure.
- citation_coverage: whether key facts carry [KBx]/[WEBx] source markers.

Topic: {state['topic']}
Keywords: {state['keywords']}

Reference material:
{context}

Article:
{article[:6000]}
"""
        try:
            report = llm.generate_json(prompt)
            if isinstance(report, dict):
                return {"quality_report": report}
        except Exception as exc:
            return {"quality_report": self._fallback_quality_report(str(exc))}

        return {"quality_report": self._fallback_quality_report("Failed to parse quality JSON")}

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
            scope = metadata.get("access_scope", metadata.get("scope", ""))
            parts.append(
                f"[KB{idx}] filename={filename}, chunk_id={chunk_id}, scope={scope}\n"
                f"{doc.get('text', '')}"
            )
        return "\n\n".join(parts) or "(none)"

    def _format_serp(self, state: SEOState, limit: int = 5) -> str:
        results = state.get("serp_results") or []
        parts = []
        for idx, r in enumerate(results[:limit], start=1):
            snippet = r.get("content") or r.get("snippet") or ""
            parts.append(f"[WEB{idx}] {r.get('title', '')} ({r.get('link', '')})\n{snippet[:800]}")
        return "\n".join(parts) or "(none)"

    def _build_context(self, state: SEOState) -> str:
        return f"## Knowledge base:\n{self._format_rag(state)}\n\n## Web search:\n{self._format_serp(state)}"

    def _build_citations(self, state: SEOState) -> List[Dict[str, Any]]:
        citations = []
        for idx, doc in enumerate((state.get("rag_docs") or [])[:8], start=1):
            metadata = doc.get("metadata") or {}
            citations.append({
                "id": f"KB{idx}",
                "type": "knowledge_base",
                "filename": metadata.get("filename"),
                "chunk_id": metadata.get("chunk_id"),
                "scope": metadata.get("access_scope", metadata.get("scope")),
                "matched_query": metadata.get("matched_query"),
                "sources": doc.get("sources", [doc.get("source")]),
                "score": doc.get("rerank_score", doc.get("rrf_score", doc.get("score"))),
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
            "suggestions": ["Check whether the LLM service is available, or regenerate the quality evaluation later."],
        }

    # ---------------- 对外的分步执行接口 ----------------

    def _config(self, thread_id: str, tenant_id: str = None) -> Dict[str, Any]:
        """构造运行配置：thread_id 用于 checkpoint；callbacks 挂载 Langfuse（可选）。"""
        config: Dict[str, Any] = {"configurable": {"thread_id": thread_id}}
        handler = observability.get_langfuse_handler(
            session_id=thread_id,
            user_id=tenant_id,
            tags=["seo_article_generation"],
        )
        if handler is not None:
            config["callbacks"] = [handler]
        return config

    def start(self, initial_state: SEOState, thread_id: str) -> List[str]:
        """第一步：执行 query 改写 + RAG + SERP + 生成标题，在生成大纲前暂停。返回 5 个标题。"""
        config = self._config(thread_id, initial_state.get("tenant_id"))
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
