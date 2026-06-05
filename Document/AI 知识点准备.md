# Rag

## 面试总回答

我当前项目里的 RAG 不是简单“向量库搜一下再交给大模型”，而是一个面向 SEO 文章生成的检索增强链路：

1. 文档上传后，先解析 PDF / MD / TXT / DOCX。
2. 使用 `RecursiveCharacterTextSplitter` 做切块，当前是 `chunk_size=512`、`chunk_overlap=128`。
3. 使用 `BAAI/bge-small-zh-v1.5` 做中文 embedding，向量维度是 512。
4. 同一批 chunk 同时写入 Milvus 和 Elasticsearch：
   - Milvus 负责语义召回。
   - Elasticsearch 负责关键词召回。
5. 检索时先做 query rewrite，生成多个检索 query。
6. 每个 query 都走 Milvus + Elasticsearch 双路召回。
7. 多路结果合并去重后，使用 FlashRank 做 rerank，最终返回 Top-K 证据。
8. 生成文章时把知识库证据和 SerpAPI 搜索结果一起传给 LLM，并返回 citations 和 quality_report。

一句话总结：

> 我的 RAG 重点是提升召回覆盖率、控制生成幻觉、让文章内容可溯源。核心实现是 query rewrite + Milvus/ES 双路召回 + FlashRank 重排 + citation + 生成后质量评估。

## 切块

### 当前项目怎么做

当前项目使用 LangChain 的 `RecursiveCharacterTextSplitter` 切块：

- `chunk_size=512`
- `chunk_overlap=128`
- 分隔符包含：段落、换行、中文句号、感叹号、问号、英文标点、空格等
- 每个 chunk 会带上 metadata，例如 `filename`、`tenant_id`、`collection_name`、`chunk_id`

项目里现在是“字符长度控制”，不是 token 级控制。面试时不要说当前已经用了 tiktoken 控 token，否则和代码不一致。

### 为什么要 overlap

Overlap 是为了解决“切块边界导致语义断裂”的问题。

比如一段话前半段讲问题，后半段讲解决方案，如果正好被切成两个 chunk，单独召回其中一个可能上下文不完整。设置 128 overlap 后，相邻 chunk 会保留一部分重复内容，能提高召回后的语义完整性。

### 为什么用 RecursiveCharacterTextSplitter

它会按优先级递归切分：

1. 先按段落切。
2. 段落太长再按换行切。
3. 还太长再按句号、问号、感叹号切。
4. 最后才按空格或字符切。

这样比简单按固定长度截断更接近自然语言结构。

### 面试回答

切块的目标不是越细越好，而是在召回粒度和上下文完整性之间做平衡。我的项目里使用 `RecursiveCharacterTextSplitter`，按段落、换行、中文标点递归切分，当前 chunk size 是 512，overlap 是 128。这样既不会让 chunk 太大引入太多噪声，也不会太小导致语义不完整。后续如果文档结构更复杂，我会进一步按 Markdown 标题、章节、页面号做结构化切块。

### 后续优化

- 用 tiktoken 或模型 tokenizer 控制 token 数，而不是只控制字符数。
- Markdown 文档按标题层级切块。
- PDF 文档保留页码，便于 citation 溯源。
- 对 FAQ、产品文档、SEO 方法论文档使用不同切块策略。
- 增加 chunk 质量检查：空 chunk、重复 chunk、过长 chunk、无意义 chunk 不入库。

## 如何 query 改写

### 当前项目怎么做

当前项目已经在 LangGraph 里增加了 `rewrite_query` 节点。

原始 query 是：

```text
topic + keywords
```

然后让 LLM 根据主题和关键词改写成 3-5 个中文检索 query，要求覆盖：

- 主题背景
- 用户痛点
- 解决方案
- FAQ
- 不同 SEO 写作角度

每个 query 都会走同一套 RAG 检索链路：

```text
query rewrite -> 多 query -> Milvus + Elasticsearch -> 合并去重 -> FlashRank rerank
```

### 为什么要 query 改写

用户输入和知识库里的表达不一定一致。

例如用户输入“AI 幻觉怎么解决”，知识库里可能写的是：

- 事实一致性校验
- 忠实度评估
- groundedness
- RAG 防编造
- 引用溯源

如果只用原始 query，可能漏召回。Query rewrite 的作用是把用户问题扩展成更贴近知识库表达的多个检索视角。

### 面试回答

我在 RAG 前面加了 query rewrite 节点，不是直接拿用户输入去搜。因为用户输入往往比较短，而且表达方式和知识库不一定一致。我的做法是让 LLM 先把 `topic + keywords` 改写成多个检索 query，覆盖背景、痛点、解决方案、FAQ 等角度，然后每个 query 都走 Milvus 和 Elasticsearch 双路召回。这样能提升 recall。为了避免召回变多后噪声变多，我最后会统一用 FlashRank rerank，只取 Top-K 证据进入生成阶段。

### 和 prompt 模版的关系

Prompt 模版主要控制“生成质量”，Query rewrite 主要控制“检索质量”。

在我的项目里：

- 标题、大纲、文章生成使用固定 prompt 结构，限制输出格式和内容方向。
- Query rewrite 是在检索前发生，用来提升召回覆盖率。
- 文章生成阶段再把 RAG 证据、网页搜索结果、用户选择的大纲一起交给 LLM。

所以不能把 query rewrite 简单理解为“控制用户输入提示词”，它更像是 RAG 检索前的查询理解层。

### 后续优化

- 对 query rewrite 的结果做去重、黑名单过滤和长度限制。
- 增加 HyDE：先生成一个假设答案，再用假设答案做向量检索。
- 根据不同业务意图生成不同 query，例如产品介绍、FAQ、竞品对比、价格方案。
- 记录每个 chunk 是被哪个 query 召回的，用于分析 query rewrite 是否有效。

## 如何双路召回

### 当前项目怎么做

项目中上传文档后，同一批 chunk 会写入两个系统：

- Milvus：存储 dense embedding，用 COSINE 相似度做语义检索。
- Elasticsearch：存储 text 字段，用 `match` 查询做全文检索。

检索时：

1. 对 query 生成 embedding。
2. Milvus 召回 Top 20。
3. Elasticsearch 召回 Top 20。
4. 两路结果按文本去重合并。
5. 使用 FlashRank 对合并后的候选统一 rerank。
6. 最终返回 Top 10。

注意：当前项目没有做“智能权重 + 归一化融合”，而是先合并去重，再交给 rerank。这样说更贴合代码。

### 为什么要双路召回

Milvus 和 Elasticsearch 解决的问题不一样：

- Milvus 适合语义相似召回，比如“幻觉治理”和“减少模型编造”。
- Elasticsearch 适合关键词精确匹配，比如品牌名、术语、型号、政策条款。

只用向量召回，可能丢掉关键词精确命中的内容；只用关键词召回，又可能召不回表达不同但语义相同的内容。所以两路结合更稳。

### 为什么要 rerank

Milvus 的向量分数和 Elasticsearch 的 `_score` 不在同一个量纲，不能简单相加或直接排序。

当前项目选择：

```text
Milvus 候选 + ES 候选 -> 去重合并 -> FlashRank rerank -> Top-K
```

FlashRank 是 cross-encoder 类重排，会同时看 query 和 passage，更适合做最终相关性排序。

### 面试回答

我的双路召回是 Milvus 稠密检索 + Elasticsearch 全文检索。Milvus 解决语义相似的问题，ES 解决关键词精确匹配的问题。两路召回后，我没有直接混合分数，因为两个系统的 score 不是一个量纲；我先按文本去重合并，再用 FlashRank 做重排，最终取 Top 10 作为 RAG 上下文。这样既保证召回覆盖，也保证最终进入 LLM 的上下文相关性更高。

### 后续优化

- Elasticsearch 中文分词优化，当前 standard analyzer 对中文不是最优。
- 引入 RRF 或加权融合，在 rerank 前做更合理的候选排序。
- 对不同来源设置召回配额，避免某一路结果完全压制另一边。
- 增加离线评测集，用 recall@k、precision@k、MRR、NDCG 评估召回和重排效果。

## 知识库

### 当前项目怎么做

当前项目的知识库以 `tenant_id + collection_name` 做隔离：

- Milvus collection 名称是 `collection_name_tenant_id`。
- Elasticsearch index 名称也是 `collection_name_tenant_id`。
- metadata 中也会冗余 `tenant_id` 和 `collection_name`，方便排查和二次校验。

这样可以避免不同租户、不同知识库之间的数据混淆。

### 知识库更新

知识库需要在以下场景更新：

- SEO 方法论更新。
- 企业产品文档升级。
- 价格、功能、政策发生变化。
- 用户发现生成内容依据过旧。
- 新增 FAQ、案例、竞品资料。

面试回答：

RAG 的质量很大程度取决于知识库质量。我会把知识库更新作为一个知识工程流程来做：文档更新后重新解析、切块、embedding，并写入 Milvus 和 ES。对于企业内部文档，要保留版本、来源、更新时间，避免模型基于过期资料生成。

### Agent 结束以后反哺知识库

文章优化或人工审核后，可以把高质量结果反哺知识库：

- 用户问题。
- 召回到的证据。
- 最终采纳的文章段落。
- 人工修改意见。
- 质量评估结果。

这些可以结构化入库，作为后续相似问题的知识来源。

面试回答：

我会把用户反馈和人工审核结果沉淀回知识库，形成闭环。比如某篇文章被人工修改过，我会记录修改前问题、修改后方案、采纳原因和对应证据。之后遇到类似主题时，RAG 不只召回原始文档，也能召回历史优化经验。



# Agent
## LangChain
### 专有名词
待填写

### 如何做上下文管理设计
(小模型不能超过 2/3的 上下文 token 限制，LLM 不能超过 50K)

如大于模型最大上下文的一般，就可以考虑使用限流上下文。具体做法是

1.统一采用 tiktoken,类似的计算出上下文大小，预留 20%的误差。

2.假如计算出来的上下文大于 模型最大上下文的 2/3，那么就采用下面的限流策略

3.滑动窗口算法+RAG 摘要，舍弃一部分上下文。

3.1.使用 LangChain 框架的 ConversationSummaryBufferMemory 组件即可，利用滑动窗口算法+摘要即可实现上下文瘦身。具体做法是：

3.2配置两个大模型，主力模型负责执行主流程，摘要模型负责后台生成摘要。

3.3配置最近的数据不超过 50K，控制成本以及减少上下文噪声。

3.4框架会自动把近期的数据全部加载进来，然后控制 token 数量不超过 50K，然后再把历史的摘要加载进来

4.通过 Langchain 库的 ChatOpenAi(GPT，qianwen,deepseek) 和 ChatAnthropic(Claude) 这两个类，Gemini 是独特的 Grpc/Rest风格，但是可以通过兼容端点代理。

### LangChain 1.1有哪些新特性
1.0 是可用，1.1 是好用

+ 摘要中间件更好用
+ 有 model.dev,已经帮我们罗列好各种 LLM 的能力
+ 更好的管理上下文

## LangGraph
### 专有名词
+ State：全局共享数据（状态 + 数据流）
+ StateGraph / MessageGraph：定义工作流图（怎么搭建图）
+ Graph(搭建好的图)
+ Node：单步执行逻辑
+ Edge：节点连接关系
+ Conditional Edge：条件分支路由
+ START / END：起止节点
+ Reducer：状态字段合并策略
+ Chain / Runnable：节点内部可调用的能力单元
+ Checkpoint：会话状态持久化/恢复
+ Store：长期记忆或跨会话数据
+ Interrupt：人工介入中断点
+ Streaming：流式输出执行过程
+ Subgraph：可复用子流程

### 如何设计 LangGraph的图，节点，边以及状态管理
### 如何处理幂等操作？为什么要处理？
### 如何处理失败回退和降级策略？
### 断点续传如何处理
### 经典组件
1. **<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">失败回退</font>**<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">给节点绑定</font>`<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">error_handler</font>`<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">捕获执行异常，将异常信息写入图状态，通过</font>**<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">条件边</font>**<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">判断失败状态，自动跳转到预设的回退节点处理。</font>
2. **<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">重试机制</font>**<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">在状态中维护重试次数，节点异常时</font>`<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">error_handler</font>`<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">累加重试计数，通过条件边判断：未达最大次数则</font>**<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">跳回当前节点重新执行</font>**<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">，达到上限则进入回退 / 降级。</font>
3. **<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">降级策略</font>**<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">基于状态里的异常类型、失败次数做路由，失败后不走主逻辑，直接路由到</font>**<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">轻量化、高可用的降级节点</font>**<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">，执行简化兜底流程，保证流程不中断。</font>
4. **<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">断点续传</font>**<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">编译图时配置</font>`<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">Checkpointer</font>`<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">持久化检查点，</font>**<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">每执行一个节点就持久化状态与执行进度</font>**<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">；服务崩溃或中断后，从最新检查点恢复，从失败的节点继续执行，实现断点续跑。</font>

一句话：

<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">LangGraph 通过</font>**<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">异常捕获 + 状态驱动 + 条件路由</font>**<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">实现失败、重试、降级，通过</font>**<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">检查点持久化</font>**<font style="color:rgb(0, 0, 0);background-color:rgba(0, 0, 0, 0);">实现断点续传，全程工作流可观测、可恢复、可降级。</font>

## DAG 实现方式-一期
### 业界常用的 RAG + Agent 工程化方案（简洁版）
#### 1) 数据与知识库层（Knowledge Pipeline）
+ Ingest/ETL：文档采集（产品文档/FAQ/竞品/政策）→ 清洗去重 → 版本化（source、时间戳、hash）。
+ Chunking & Metadata：按标题层级+语义切块；打上 product/feature/version/lang/audience 等元数据。
+ 双索引：ES（稀疏）+ Milvus（稠密）；写入时做质量校验（空块、重复块、过长块）。
+ 离线评测集：沉淀一批真实 query + 标注答案/证据，作为回归基线。

#### 2) 在线检索层（Retrieval Service）
+ Query Agent（查询理解）：意图分类 + 实体抽取 + query rewrite（生成多 query）。
+ Hybrid Retrieval：ES + Milvus 双路召回 → 归一化融合（RRF/加权）→ TopK。
+ Rerank：Cross-Encoder/LLM rerank → TopN 证据切片。
+ Citation Gate：强制回答必须引用证据切片（无证据则降级为“需要补充资料/建议入库”）。

#### 3) 生成与工作流层（Agentic Workflow）
+ 生成文章工作流，使用 LangChain自带的工作流
+ 优化文章工作流，使用 LangGraph，比较复杂。

#### 4) 质量与可观测（Evaluation & Observability）
+ Langfuse：全链路 tracing（prompt/模型/检索命中/延迟/成本/失败原因）+ prompt 版本管理。
+ Ragas：离线/在线抽样评测（faithfulness、context precision/recall 等）→ 形成质量看板。
+ 自动回归：每次改 prompt/检索参数/模型路由，都跑评测集对比基线，防止“改崩”。

#### 5) 成本与稳定性（Production Hardening）
+ Model Router：按复杂度/风险路由模型（便宜模型优先，关键步骤再用强模型）。
+ 语义缓存：相似 query 命中缓存，降本提速。
+ 降级策略：检索失败→改写 query→扩大召回→仍失败则返回“需补资料”并自动生成入库任务。

## 多 Agent实现方式-二期
待实现，基于一期，主要是一组 Agent 一起并发实现优化文章。其中会遇到的挑战。



## 父子 Agent实现方式-三期
待实现，基于二期，多 Agent 共同处理任务的时候，某个 Agent 还能继续拆分子 agent

# 优化 & 监控
## 如何提升召回率
+ 语义切块+overLap
+ 双路召回
+ query 改写
+ 降低余弦量的值

## 如何提升精准度
+ 语义切块+overlap
+ 双路召回
+ query 改写
+ 定义合理的余弦量最低值，以及双路召回权重



## 如何降低 AI 使用的成本
## 如何做语义缓存
## 如何提升文章的忠实度？
## 如何提升文章的相关性？
## 如何减少大模型幻觉
## 如何更好得写提示词
## 如何监控 Agent 工作流的进度和状态
# 技术选型
## 大模型如何选型
## Embedding 如何选型
## Java 和 Python 如何选型
# AI 编程
面试官会问我，如何用 AI 编程提升效率，我现在主要用 CUrsor,Trae

需要设计，如何用 AI 提升效率，涉及软件开发全流程。举个例子我能想到的就是，产品发布 PRD，然后 AI 能够读取到 PRD（比如通过 MCP 接口），然后拉取分支，开始干活，编写单元测试以及测试用例，然后用户体验验收，然后压测，最终交付上线。可能要涉及到 AI 如何控制整个软件生命周期，以及不让 AI 瞎写导致出问题。

#  面试常见追问（标准答案）
### Q1：你怎么评估“文章优化”是不是有效？
我分两层：

+ **离线质量**：Ragas（faithfulness/context precision等）+ SEO Rubric（覆盖度/结构/重复率）
+ **线上效果**：GSC（CTR/排名/展现/点击）+ 观察窗口对比基线，必要时做灰度/分组

### Q2：怎么避免 Agent 胡改、改崩文章？
三道闸：

+ **Plan 约束**：优先 Small Patch，限制改动比例/是否允许改标题
+ **Verifier Gate**：Ragas + 结构化 rubric + Diff Safety（敏感结论必须引用）
+ **可回滚**：版本化与灰度，指标恶化自动回滚并复盘

### Q3：为什么一定要多 Agent？单 Agent 也能写啊
多 Agent 解决的是“生产系统的可控性”：

+ 诊断/规划/执行/验证拆开，每步可观测、可替换、可并行
+ 失败可定位（是检索、结构、证据还是内链），并自动选择下一步
+ 真正做到闭环迭代与回归，而不是一次性生成

### Q4: 可观测（Observable）是什么意思
系统上线后，你能看得清楚它每一步在做什么、为什么这样做、哪里慢/贵/错了。

+ 例子：一次生成里，检索召回了哪些切片、rerank 排序结果、用了哪个模型、花了多少 token、最终答案引用了哪些证据、失败点在哪（超时/命中差/评测不通过）。
+ 你这里的落地：用 Langfuse 做 tracing、日志、成本与延迟看板、prompt/参数版本记录。

### Q5: 可回归（Regression-testable / Reproducible）是什么意思
你改了 prompt、检索参数、模型、分块策略后，能稳定复现并验证：质量有没有变好/变差，而不是“凭感觉”。

+ 例子：每次改动都跑一套固定评测集（历史关键词、QA 样本），对比改动前后的 faithfulness/相关性/命中率/成本，不达标就不发布或回滚。
+ 你这里的落地：用 Ragas + 自定义 rubric 做自动评测，并绑定到版本（prompt/检索参数/模型路由）。

### Q6: 可降级（Degradable / Graceful fallback）是什么意思
当某个环节出问题（检索失败、模型超时、成本超预算、外部工具不可用），系统不会“直接挂掉”，而是自动切换到更稳的备选路径，保证可用性。

+ 例子：
+ 向量检索不可用 → 先用 ES 关键词检索顶上
+ rerank 超时 → 退化为不 rerank 或降低 topK
+ GPT‑4 超预算 → 路由到更便宜模型 + 缓存命中优先
+ 证据不足 → 返回“需要补充资料/触发入库任务”，而不是编造
+ 你这里的落地：Model Router、语义缓存、分级超时/重试、无证据不输出等策略。

一句话总结：

+ 可观测让你“定位问题快”；可回归让你“改系统不翻车”；可降级让你“线上稳定不崩”。

# 知识
## 专有名词
| 名词 | 一句话核心定义 | 面试考点 |
| --- | --- | --- |
| **LLM** | 大语言模型，Agent 的 “大脑”，负责理解、推理、生成文本 | 模型选型、上下文窗口、幻觉、推理能力 |
| **Agent** | 具备规划、记忆、工具调用、反思能力的自主智能体 | 核心能力、工作流程、与普通 LLM 的区别 |
| **A2A** | 多智能体之间分工协作、任务流转的架构模式 | 多智能体优势、任务拆分、协同机制 |
| **MCP** | 模型与工具之间标准化调用协议，基于 JSON-RPC | 工具调用规范、与 Function Calling 区别 |
| **ACP** | 智能体与智能体之间的通信协议 | 与 MCP 的区别、A2A 协作底层支撑 |
| **Skill** | 可复用、标准化的原子能力单元，类似 AI 插件 | 与工具区别、技能编排、生态化 |
| **OpenClaw** | AI 本地执行平台，负责操作系统级真实落地操作 | 架构定位、与 Agent/Skill/MCP 的关系 |
| **RAG** | 检索外部知识再生成，解决幻觉与知识过时 | 流程、向量库、分块、重排序、优缺点 |
| **CoT** | 思维链，让模型分步推理再给出答案 | 提升推理、复杂任务、Prompt 写法 |
| **ReAct** | 思考 → 行动 → 观察 → 再思考，Agent 标准范式 | Agent 执行流程、工具调用循环 |
| **Tool Use** | 模型调用外部工具 / API / 数据库 / 文件等能力 | 函数调用、参数构造、异常处理 |
| **Reflection** | 执行后自检、评估、纠错、重试的能力 | 提升可靠性、减少错误、自我优化 |
| **Memory** | Agent 的短期上下文记忆与长期向量记忆 | 记忆类型、存储方式、RAG 结合 |
| **Embedding** | 文本转为向量，用于语义检索与相似度匹配 | 向量库、RAG、长期记忆实现 |
| **Orchestration** | 多 Agent / 多工具 / 多步骤的流程编排与调度 | 任务管理、状态同步、异常恢复 |
| **Vector DB** | 存储向量、支持高效语义检索的数据库 | RAG 必备、常见选型、检索流程 |
| **Hallucination** | 模型编造虚假信息、事实错误 | 产生原因、如何缓解（RAG / 反思 / 校验） |
| **Prompt** | 给 LLM 的指令，决定行为与输出格式 | 工程技巧、Few-shot、结构化输出 |
| **Token** | LLM 处理文本的最小计算单位 | 上下文长度、成本限制、截断问题 |
| **Planning** | 将复杂任务自动拆解为多步可执行子任务 | Agent 核心能力、任务拆解逻辑 |


## MCP
## ACP
## Agent
### Harness
这个很重要，是所有 Agent 框架的底层架构，属于 AI 的控制系统。用于回答如何控制 AI 更好得工作。

## A2A
## Skill
### 是什么
一类似 Cursor rule，我们可以编写，然后不用每次都和 AI 说。是一种结构化的，可复用的能力。

### 在哪里可以下载
Anthropic 官网，github 等地方

### 怎么用 
以对应的格式，写好skill，然后每次调用 API 的时候传递过去，或者云端上传，本地 1 每次传递一个 assistId 即可

## OpenClaw
## Hermes(爱马仕)




# 重点
上述是准备 AI 的全量知识，我希望把重点放在下面三个上，到时候方便面试集中精力


## 如何解决 AI 幻觉问题，提升文章生成质量

### 结合当前项目的整体链路
当前项目是一个 SEO 文章生成 RAG 系统，核心链路是：

1. 用户上传 PDF / MD / TXT / DOCX 文档。
2. `DocumentProcessor` 解析文档文本。
3. `TextChunker` 使用 `RecursiveCharacterTextSplitter` 切块，当前配置是 `chunk_size=512`，`chunk_overlap=128`，分隔符包含段落、换行、中文句号、感叹号、问号等。
4. `EmbeddingService` 使用 `BAAI/bge-small-zh-v1.5` 生成 512 维向量。
5. `VectorStore` 同时写入 Milvus 和 Elasticsearch：
   - Milvus 存向量，用于语义召回。
   - Elasticsearch 存全文，用于关键词召回。
   - 按 `collection_name + tenant_id` 做物理隔离，避免不同租户知识混淆。
6. 查询时 `RetrievalEngine` 做双路召回：
   - Milvus：向量相似度召回，适合语义相近但关键词不完全一致的问题。
   - Elasticsearch：全文召回，适合精确词、品牌词、术语、型号等关键词。
7. `RerankService` 使用 FlashRank 多语言重排模型，把两路候选统一重排，最终返回 Top-K。
8. `SEOWorkflow` 使用 LangGraph 编排：
   - `retrieve_rag` 检索知识库。
   - `search_serp` 调用 SerpAPI 获取实时网页信息。
   - `generate_titles` 生成标题。
   - 用户选择标题后 `generate_outlines` 生成大纲。
   - 用户选择大纲后 `generate_article` 生成文章。

面试表达：我不是直接把用户问题丢给大模型，而是先用 RAG 和搜索引擎构造可信上下文，再让模型在上下文范围内生成，减少模型凭空编造。

### 提升召回率和精准度

#### 1. 双路召回
当前项目用了 Milvus + Elasticsearch 的双路召回：

- 向量召回解决“语义相似但表达不同”的问题，比如用户问“如何降低 AI 编造内容”，知识库写的是“幻觉治理”。
- 全文召回解决“关键词必须命中”的问题，比如品牌名、产品型号、专有名词、法规条款。
- 两路召回的分数体系不同，所以项目里没有直接按原始分数排序，而是先合并去重，再交给 FlashRank 重排。

面试表达：向量召回偏 recall，关键词召回偏 precision，重排负责最终相关性排序。

#### 2. 切块策略
当前项目使用 512 字符左右的 chunk，128 overlap。这样做的原因：

- chunk 太大：召回粒度粗，容易把无关内容一起塞给模型，降低答案忠实度。
- chunk 太小：上下文不完整，模型拿不到完整因果关系，容易断章取义。
- overlap 可以缓解句子、段落被切断的问题，让跨段信息在相邻 chunk 中保留。

后续可以优化：

- 按标题、段落、Markdown 层级做结构化切块，而不是只按字符切。
- 在 metadata 里记录 `doc_id`、`section_title`、`page_number`、`chunk_id`，方便答案溯源。
- 对 SEO 文档可以按“标题、问题、解决方案、结论”做语义切块，提高文章生成时的上下文完整性。

#### 3. Embedding 选型
当前项目使用 `BAAI/bge-small-zh-v1.5`，适合中文语义检索，维度 512，速度和成本较低。

选型时重点看：

- 是否适合中文。
- 向量维度和存储成本。
- 召回效果，最好用自己的业务数据评测，而不是只看榜单。
- 是否需要多语言，如果中英文混合，就考虑 bge-m3、multilingual-e5 等模型。

面试表达：Embedding 不是越大越好，业务中要在召回效果、推理速度、存储成本之间平衡。

#### 4. Query 改写
当前项目的生成链路里，RAG 查询是 `topic + keywords`。这是简单有效的第一版，但还有提升空间：

- 同义词扩展：把“幻觉”扩展为“编造、事实错误、不忠实、hallucination”。
- 多查询改写：把一个问题拆成多个检索 query，例如“召回率怎么提升”“RAG 如何防幻觉”“文章忠实度怎么评估”。
- HyDE：先让模型生成一个理想答案草稿，再用草稿做向量检索，提升语义召回。
- 意图拆解：把用户想生成 SEO 文章的需求拆成“主题背景、用户痛点、解决方案、竞品信息、FAQ”等多个检索方向。

面试表达：Query 改写的目标不是让问题变长，而是让检索 query 更接近知识库中的表达方式，提高召回率和覆盖面。

### 解决 AI 幻觉

#### 1. 没有检索结果怎么办
如果 RAG 没有召回有效内容，不能让模型自由发挥。应该做降级：

- 明确告诉模型“知识库未检索到相关内容，不要编造事实”。
- 允许模型只输出通用建议，但要标注“非知识库依据”。
- 触发 SerpAPI 网络搜索，用实时网页补充。
- 对关键业务场景返回“缺少资料，请补充文档”，而不是生成看似完整但不可靠的内容。

当前项目里 `_format_rag()` 在没有 RAG 内容时会返回“（无）”，这可以继续加强：在 prompt 中明确要求模型遇到“（无）”时不要伪造知识库事实。

#### 2. 检索内容和模型知识冲突怎么办
如果检索内容与模型预训练知识冲突，优先级应该是：

1. 用户上传的知识库。
2. 实时搜索结果。
3. 模型自身知识。

原因是知识库通常代表企业内部事实、产品规则或最新资料。面试时可以说：我的策略是“上下文优先”，模型只负责语言组织和推理，不让它覆盖业务事实。

可落地做法：

- Prompt 里写清楚“必须优先依据 knowledgeBase，不得使用与 knowledgeBase 冲突的信息”。
- 生成后做事实一致性校验，让模型逐条检查文章中的关键事实是否能在 RAG 或网页结果中找到依据。
- 对没有依据的句子打标或删除。
- 输出引用来源，比如 chunk_id、文件名、网页链接，方便人工复核。

#### 3. 限制模型自由发挥
当前项目已经做了几件事：

- 标题和大纲阶段要求模型返回 JSON，降低格式漂移。
- 文章阶段把 `knowledgeBase` 和 `web_info` 单独传入 prompt。
- 通过 LangGraph 拆成标题、大纲、文章三个阶段，并在标题和大纲处加入人工选择，减少一次性生成导致的方向偏差。

还可以增强：

- 在系统 prompt 中加入“只能基于参考资料回答；没有依据要说明无法确认”。
- 要求模型输出“事实来源映射”，例如每段对应哪些 chunk。
- 对文章做二次校验：相关性、忠实度、是否包含无依据事实。

### 提升文章生成质量

当前项目不是一次性生成文章，而是三阶段生成：

1. 先生成 5 个标题，让用户选择方向。
2. 再生成 3 套大纲，让用户选择结构。
3. 最后按选定大纲生成完整文章。

这样做的好处：

- 降低长文本一次生成的不确定性。
- 用户可以在关键决策点介入，避免文章跑偏。
- 标题、大纲、正文分别优化，更符合 SEO 内容生产流程。

文章质量可以从四个维度提升：

- 忠实度：内容是否能被知识库或网页搜索结果支持。
- 相关性：是否紧扣 topic、keywords 和用户意图。
- 结构性：标题、大纲、段落是否符合 SEO 文章结构。
- 可读性：语言是否自然、信息是否完整、是否有重复和空话。

可扩展实现：

- 生成后增加 evaluator 节点，对文章进行评分。
- 使用 LLM-as-a-Judge 检查“是否忠实于 RAG 上下文”。
- 对低分文章自动触发重写，重写时只修改问题段落。
- 加入引用和来源，让文章可追溯。

### Langfuse 如何做全链路监控

当前项目还没有真正接入 Langfuse，但可以作为下一步可观测性建设。Langfuse 适合记录 LLM 调用、RAG 检索、Agent/DAG 节点耗时、token、成本、评分等。

#### 1. Trace 设计
一次文章生成用一个 trace，对应一个 `thread_id`：

- trace name：`seo_article_generation`
- user_id：`tenant_id`
- session_id：`thread_id`
- metadata：`topic`、`keywords`、`collection_name`、`llm_provider`

#### 2. Span 设计
每个关键步骤记录一个 span：

- `document_parse`：文档解析耗时、文件类型、文本长度。
- `chunking`：chunk 数量、chunk_size、chunk_overlap。
- `embedding`：embedding 模型、向量维度、耗时。
- `milvus_search`：召回数量、top score、耗时。
- `es_search`：召回数量、top score、耗时。
- `rerank`：候选数量、Top-K、rerank_score、耗时。
- `serp_search`：搜索结果数量、抓取成功率、耗时。
- `generate_titles`：输入 token、输出 token、耗时、模型、费用。
- `generate_outlines`：输入 token、输出 token、耗时、模型、费用。
- `generate_article`：输入 token、输出 token、耗时、模型、费用。

#### 3. 监控指标
RAG 指标：

- recall 命中率：人工标注答案所需 chunk 是否被召回。
- precision：Top-K 中真正相关 chunk 的比例。
- MRR / NDCG：相关 chunk 排名是否靠前。
- empty retrieval rate：无召回比例。
- rerank 前后相关性提升。

生成指标：

- faithfulness：文章事实是否被 RAG / SERP 支持。
- relevance：是否围绕 topic 和 keywords。
- groundedness：每段是否能找到依据。
- format correctness：JSON 或 Markdown 格式是否稳定。
- human acceptance rate：用户是否接受标题、大纲、文章。

成本和性能指标：

- 每次生成的输入 / 输出 token。
- 每个模型的调用次数和费用。
- RAG 检索耗时、SerpAPI 耗时、LLM 生成耗时。
- 端到端耗时。
- 不同模型（DeepSeek / 通义千问 / 豆包）的质量、成本、延迟对比。

#### 4. 面试表达
可以这样回答：

我会把一次文章生成看作一个 trace，把 RAG 检索、Serp 搜索、标题生成、大纲生成、正文生成都作为 span。这样不仅能看到最终文章质量，还能定位问题来自哪里：是召回阶段没召回，还是重排把相关内容排低了，还是 prompt 没约束好，还是模型本身生成质量差。对于 RAG 系统，不能只看最终回答，要把检索质量、上下文质量、生成质量和成本延迟全部串起来看。

### 当前项目已经落地的优化点

#### 1. Query Rewrite + 多查询召回
原来项目只用 `topic + keywords` 做一次检索，现在在 LangGraph 中增加了 `rewrite_query` 节点：

- 先让 LLM 根据主题和关键词生成 3-5 个检索 query。
- 每个 query 分别走 Milvus + Elasticsearch 双路召回。
- 合并所有候选 chunk，并按文本去重。
- 最后仍然用原始 query 作为主意图，通过 FlashRank 做统一重排。

面试表达：

以前是单 query 检索，容易因为用户表达和知识库表达不一致导致漏召回。现在我在 RAG 前面加了一层 query rewrite，把主题拆成多个检索角度，再做多查询召回，可以提升召回覆盖率；同时最后统一 rerank，避免召回变多以后引入太多噪声。

#### 2. Citation 溯源
生成文章时，项目现在会把 RAG 和网页搜索结果格式化为带编号的上下文：

- 知识库来源：`[KB1]`、`[KB2]`，包含文件名、chunk_id、matched_query。
- 网页来源：`[WEB1]`、`[WEB2]`，包含标题和链接。
- Prompt 中要求模型对关键事实尽量标注 `[KBx]` 或 `[WEBx]`。
- `/api/generate/article` 接口会额外返回 `citations`，前端会展示引用来源和内容预览。

面试表达：

我不只生成文章，还把生成依据一起返回。这样文章里的事实可以追溯到知识库 chunk 或网页链接，方便人工复核，也能减少模型把无依据内容写成事实。

#### 3. 生成后质量评估
文章生成后，LangGraph 会继续执行 `quality_check` 节点，对文章做 LLM-as-a-Judge 评估：

- `faithfulness`：是否忠实于 RAG / SERP 参考资料。
- `relevance`：是否围绕 topic 和 keywords。
- `structure`：是否符合 SEO 文章结构。
- `citation_coverage`：关键事实是否有来源标注。
- `overall`：综合分。
- `risks` / `suggestions`：风险和改进建议。

接口会返回 `quality_report`，前端会展示质量分、风险和建议。

面试表达：

我没有把生成结果当成最终答案直接交付，而是在生成后加了质量评估节点。这样可以量化文章质量，也能定位问题是忠实度不够、相关性不够、结构不好，还是引用覆盖不足。

#### 4. 前端可观测展示
生成文章后，前端会展示：

- Query 改写结果。
- 质量评估分数。
- 风险和建议。
- 引用来源列表。

面试表达：

这部分是为了让 RAG 链路可解释。面试或演示时，我可以直接展示：用户输入主题后，系统改写了哪些 query、召回了哪些知识、文章用了哪些来源、最终质量评分是多少。

### 下一步可以继续优化

- 接入 Langfuse，把 query rewrite、Milvus 检索、ES 检索、rerank、SerpAPI、LLM 生成、质量评估都记录为 trace / span。
- 增加自动重写机制：如果 `quality_report.overall` 或 `faithfulness` 低于阈值，自动带着评估建议重写文章。
- 优化 Elasticsearch 中文分词，当前使用 standard analyzer，对中文关键词检索不是最优，可以考虑 IK 分词或内置中文分析方案。
- 优化切块策略，按标题和段落结构切块，提高上下文完整性。
- 增加离线评测集，定期评估召回率、精确率、重排效果和生成质量。

## 多Agent 设计
+ 如何定义 每个 Agent 的边界和能力
+ 如何限制Agent 不乱改
+ 如何做到可观测、可回归、可降级
+ 如何监控每个 Agent 的运行状态和执行质量
+ Agent 组最终融合的时候，如何保证质量的？（可能一个 Agent 有问题会导致全盘失败）
+ LangChain + LangGraph
+ Harness底层思想,如何控制 AI 工作
+ 一期使用 DAG，之后升级为多 Agent 共同协作



