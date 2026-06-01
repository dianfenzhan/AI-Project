# AI 应用开发学习路线
> **技术栈**：Python · LangChain · LangGraph  
**四层架构**：RAG（双路召回）→ DAG 编排 → 多 Agent → AI 监控  
**目标**：面试 AI 应用开发工程师，能讲清完整链路与可演示 Demo
>

---

## 路线总览
```latex
┌─────────────────────────────────────────────────────────────┐
│  ④ AI 监控：Trace / 成本 / RAG 质量 / 告警                   │
├─────────────────────────────────────────────────────────────┤
│  ③ 多 Agent：分工、并行优化、Judge 合并、质量门禁             │
├─────────────────────────────────────────────────────────────┤
│  ② DAG（LangGraph）：State、条件边、Checkpoint、子图并行      │
├─────────────────────────────────────────────────────────────┤
│  ① RAG 双路召回：Dense + Sparse → RRF → Rerank → Grounding   │
└─────────────────────────────────────────────────────────────┘
```

| 环节 | 解决什么问题 | 建议学习周数 |
| --- | --- | --- |
| RAG 双路召回 | 答得有依据、专有名词不漏召回 | 1～1.5 周 |
| DAG | 流程可控、可重试、状态可追踪 | 1 周 |
| 多 Agent | 复杂任务拆分、并行、选优 | 1～1.5 周 |
| AI 监控 | 可排障、可迭代、能量化质量 | 贯穿全程，集中 0.5 周 |


**讲解顺序**（自下而上，听众好懂）：① → ② → ③ → ④  
**实现顺序**：① 跑通检索 → ② 接 LangGraph → ③ 加并行 Agent → ④ 从第 ② 步起接 Langfuse/LangSmith

---

## 贯穿式 Demo 建议
用一个项目串起四层，面试时只讲这一条链路：

**「品牌知识库 + SEO 文章优化」**

```latex
用户输入（关键词 / 初稿）
  → [①] Dense(Chroma) + Sparse(BM25) → RRF → BGE-Rerank → contexts
  → [②] LangGraph：research → draft（串行 DAG）
  → [③] 并行：structure / keyword / readability Agent → Judge merge
  → [④] 每节点 Langfuse trace；记录 retrieval_hit、seo_score、token
  → 输出终稿 + citations
```

---

## ① RAG：双路召回
### 要掌握什么
+ **稠密路**：Embedding + 向量库（语义相似）
+ **稀疏路**：BM25 / 全文检索（型号、SKU、专有名词）
+ **融合**：RRF（`k≈60`）优于简单加权（分数尺度不一致）
+ **精排**：Cross-Encoder（如 BGE-Reranker）对 top-20 重排
+ **工程**：分块策略、metadata 过滤、空检索处理

### 推荐开源项目
#### 1. [iuyup/Enterprise-Rag-Agent](https://github.com/iuyup/Enterprise-Rag-Agent)
| 项 | 说明 |
| --- | --- |
| **定位** | 企业级 RAG 2.0：双路并发召回 + RRF + BGE 精排 |
| **双路** | FAISS（稠密）+ BM25（稀疏） |
| **精读目录** | `src/retrieval/`、`src/processing/`、`src/pipeline/` |
| **适合** | 快速看清「双路 → 融合 → 重排」完整代码结构 |


### 本环节验收标准
- [ ] 能白板画出：Query → 双路 top-k → RRF → Rerank → Context
- [ ] 能解释：为何 SKU/型号场景 BM25 不能省
- [ ] 本地跑通至少一个 hybrid 检索 demo

---

## ② DAG：LangGraph 编排
### 要掌握什么
+ `StateGraph` + `TypedDict` 共享状态
+ 固定边 vs `add_conditional_edges`（分支 / 循环）
+ `ToolNode` + ReAct 单 Agent 环
+ `MemorySaver` / Postgres checkpointer（断点恢复）
+ 子图（subgraph）与并行 fan-out / fan-in

### 推荐开源项目
#### 1. [harshv2013/multi-agent-research-pipeline](https://github.com/harshv2013/multi-agent-research-pipeline)
| 项 | 说明 |
| --- | --- |
| **定位** | LangGraph 多节点流水线（Python，结构清晰） |
| **DAG** | Supervisor 路由 + Researcher / Writer / Reviewer |
| **精读文件** | `workflows/graph_builder.py`、`workflows/checkpointer.py`、`agents/` |
| **适合** | 学条件边、质量环、状态在节点间如何传递 |




### 官方必读
| 资源 | 链接 |
| --- | --- |
| LangGraph 文档 | [https://docs.langchain.com/oss/python/langgraph/overview](https://docs.langchain.com/oss/python/langgraph/overview) |
| LangChain Academy | [https://academy.langchain.com/courses/intro-to-langgraph](https://academy.langchain.com/courses/intro-to-langgraph) |
| LangGraph 源码示例 | [https://github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) |


### 本环节验收标准
- [ ] 手写 3 节点串行图：retrieve → draft → validate
- [ ] 加 conditional edge：分数低则回到 draft
- [ ] 开启 checkpoint，能从中断点 resume

---

## ③ 多 Agent
### 要掌握什么
+ **串行编辑部**：Research → Write → SEO → Review（一期）
+ **并行 fan-out**：多维度同时改稿 → Judge 合并（二期）
+ 与 DAG 关系：多 Agent 是 **图里的多个 node**，不是多个独立 bot
+ 冲突与门禁：Fidelity / SEO 阈值 / 品牌词不可删

### 推荐开源项目
#### 1. [KartikPawade/Marketing-and-Growth-Multi-Agent-System](https://github.com/KartikPawade/Marketing-and-Growth-Multi-Agent-System)
| 项 | 说明 |
| --- | --- |
| **定位** | LangGraph 6 Agent 内容流水线 + FastAPI + 条件 QA 门禁 |
| **多 Agent** | Research → Strategy → Content → QA → Analytics → Publish |
| **精读文件** | `app/graph/builder.py`、`app/graph/state.py`、`app/agents/` |
| **适合** | 学「内容类」多 Agent 分工 + 失败则 halt 的生产模式 |




### 本环节验收标准
- [ ] 能区分「并行子任务」vs「6 个 Agent 各写一篇」
- [ ] 在已有 DAG 上加 2～3 个并行 SEO 分支 + merge node
- [ ] 面试能画：一期串行 → 二期 parallel + judge

---

## ④ AI 监控（可观测性）
### 要掌握什么
| 类型 | 关注指标 | 说明 |
| --- | --- | --- |
| **链路追踪** | 每 node 输入/输出、耗时、父子 span | LangGraph 每个 node 一条 span |
| **RAG 质量** | 空检索率、recall@k、引用是否命中 | 检索失败要在监控里可见 |
| **生成质量** | 忠实度、SEO 分、人工反馈 | LLM-as-judge 或规则分 |
| **成本 SLA** | token、$/req、P95 延迟 | 按 Agent/模型拆分 |


### 推荐开源项目
#### 1. [langfuse/langfuse](https://github.com/langfuse/langfuse)
| 项 | 说明 |
| --- | --- |
| **定位** | 开源 LLM 工程平台（MIT），可自托管 |
| **能力** | Trace、Prompt 版本、Eval、Dataset、成本统计 |
| **集成** | LangChain / LangGraph、OpenTelemetry、OpenAI SDK |
| **适合** | **首选**：与 LangGraph 栈一致，面试可演示 UI |




### 
### 本环节验收标准
- [ ] LangGraph 项目接入 Langfuse ，一次请求可见完整 trace
- [ ] 自定义 metadata：`retrieval_hit`、`dense_count`、`sparse_count`、`seo_score`
- [ ] 能回答：检索为空时如何在监控里告警

---

## 仓库速查表
| 环节 | 主推仓库 1 | 主推仓库 2 |
| --- | --- | --- |
| **RAG 双路** | [Enterprise-Rag-Agent](https://github.com/iuyup/Enterprise-Rag-Agent) | [all-in-rag](https://github.com/datawhalechina/all-in-rag) |
| **DAG** | [multi-agent-research-pipeline](https://github.com/harshv2013/multi-agent-research-pipeline) | [agent-service-toolkit](https://github.com/JoshuaC215/agent-service-toolkit) |
| **多 Agent** | [Marketing-and-Growth-Multi-Agent-System](https://github.com/KartikPawade/Marketing-and-Growth-Multi-Agent-System) | [MAGEO](https://github.com/Wu-beining/MAGEO) |
| **AI 监控** | [langfuse](https://github.com/langfuse/langfuse) | [phoenix](https://github.com/Arize-ai/phoenix) |


---

## 4～6 周学习计划
### 第 1～2 周：RAG 双路
| 天 | 任务 |
| --- | --- |
| 1～2 | 读 all-in-rag 混合检索章节；理解 RRF |
| 3～5 | Clone Enterprise-Rag-Agent，跑通 ingest + hybrid search |
| 6～7 | 自建最小 demo：Chroma + rank_bm25 + RRF（约 60 行） |


### 第 3 周：DAG
| 天 | 任务 |
| --- | --- |
| 1～2 | LangGraph 官方 Quickstart + Academy 前几章 |
| 3～4 | 精读 multi-agent-research-pipeline 的 `graph_builder.py` |
| 5～7 | 实现：retrieve → draft → seo_validate 串行图 + checkpoint |


### 第 4 周：多 Agent + 监控接入
| 天 | 任务 |
| --- | --- |
| 1～3 | 参考 KartikPawade 的 graph，加 3 路并行 SEO node + judge |
| 4 | 读 MAGEO 的 Editor 多候选 + Evaluator 选优思路 |
| 5～7 | 接入 Langfuse；为 retrieve / merge / judge 打 span 和 metadata |


### 第 5～6 周：整合与面试准备
| 天 | 任务 |
| --- | --- |
| 1～3 | 四层合并为一个可演示项目；写 README 架构图 |
| 4～5 | 准备 1 分钟 / 3 分钟项目介绍；白板图练 3 遍 |
| 6～7 | 模拟追问：RRF 原理、并行冲突、空检索、成本优化 |


---

## 面试讲解提纲（3 分钟）
1. **业务**：品牌知识库驱动的 SEO 内容优化，要 grounded、可引用。  
2. **RAG**：双路召回解决「语义懂但术语漏」；RRF 融合 + Rerank 精排。  
3. **DAG**：LangGraph 管理 state；一期串行，二期加并行子图，仍在同一张图。  
4. **多 Agent**：结构 / 关键词 / 可读性并行 patch，Judge 按 SEO 分与品牌规则合并。  
5. **监控**：Langfuse 全链路 trace；重点看 retrieval_hit 与各 Agent 耗时/token。

---

## 常见追问速答
| 问题 | 要点 |
| --- | --- |
| 为什么双路？ | 向量抓语义，BM25 抓 SKU/型号/固定术语；单路 recall 不够 |
| RRF vs 加权？ | 分数尺度不同，RRF 只看排名，k≈60，工程上更稳 |
| 多 Agent 是否同时写全文？ | 否；并行改不同维度或出多候选，编排层 merge |
| DAG 和 CrewAI 区别？ | LangGraph 显式 state/图/ checkpoint；更适合复杂分支与生产 |
| 监控看什么？ | 不只 LLM 延迟：空检索、融合 top-k、哪条 Agent 跑偏 |


---

## 相关资源索引
### GEO / SEO 扩展（可选）
| 资源 | 链接 |
| --- | --- |
| GEO 资源列表 | [awesome-generative-engine-optimization](https://github.com/amplifying-ai/awesome-generative-engine-optimization) |
| GEO 论文实现 | [GEO-optim/GEO](https://github.com/GEO-optim/GEO) |


### 平台型 RAG（深入阅读用）
| 资源 | 链接 |
| --- | --- |
| RAGFlow（混合检索源码） | [infiniflow/ragflow](https://github.com/infiniflow/ragflow) → `rag/nlp/search.py` |
| Haystack（BM25 + Embedding + RRF） | [deepset-ai/haystack](https://github.com/deepset-ai/haystack) |


---

## 文档维护
| 字段 | 值 |
| --- | --- |
| 创建日期 | 2026-05-30 |
| 技术栈版本建议 | Python 3.11+ · langgraph ≥ 0.2 · langchain ≥ 0.3 |
| 说明 | 仓库 Star/接口可能变化，clone 前请在 GitHub 查看最新 README |


---

_本文档为学习路线整理，与当前 _`v2-privilege`_ 业务代码无耦合，可单独拷贝到其他目录使用。_

