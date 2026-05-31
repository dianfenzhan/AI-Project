# Rag
## 切块
如何语义分块，如何 overlap

### 方案一：
RecursiveCharacterTextSpliter实现段落，标点符号以及空格切分

tiktoken 可以控制分块文本在固定长度以内

然后 overlap 100个 token

### 方案二：
side LLM，帮助切块，真正实现语义切分，并且实现 overlap

## 如何 query 改写
### 方案一
提示词模版+控制输入

我们生成文章的业务流程是三段式生成的，主要通过 主题+关键词-》标题-》大纲-》正文。

我们会在后台配置一个提示词模版，只让用户输入变量信息，这个可以有效控制提示词质量。由于上下文不是很多，因此我们会把全量上下文拼接以后一起给到LLM。

### 方案二
小模型做上下文摘要+滑动窗口+query 改写

大模型做核心生成

我们文章优化的流程就相对复杂很多，上下文需要涵盖生成文章的上下文，SEO 方法论，每次的解决方案以及最后的效果，因此我们采取三部分数据作为大模型的上下文

+ 最近 2 次的解决方案以及反馈结果，包括全量的正文
+ 之前改动的摘要
+ RAG 出 SEO 的相关方法论
+ 常见此类问题的解决方案（动态维护）

## 如何双路召回
切块，分别存入 ES 和 Milvus

Milvus 稠密检索 + ES BM25 稀疏检索，智能权重+归一化处理，最终 rerank 出 10 个切块。

## 知识库
### 知识库更新
SEO 方法论更新，企业产品文档升级的时候需要更新，保证知识库的时效性。

### Agent 结束以后，反哺知识库
优化文章以后，把问题，原因以及解决方案结构化入库，为之后优化提供标准。



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
+ 提升召回率、精准度（提升 RAG 质量），比如双路召回
+ 解决幻觉问题（针对没有检索出来或者检索出来的文本和训练知识互斥怎么办？）
+ 提升生成质量（提升文章的忠实度和正相关性）
+ 结合监控 Langfuse 如何做到监控上述指标，以及全链路监控，包括但不限于召回率，精准度，文章的忠实度和正相关性以及 token 使用数量、经费以及 AI 回答的时间以及 Rag 和 agent 消耗时长以及 token 数等。

## 多Agent 设计
+ 如何定义 每个 Agent 的边界和能力
+ 如何限制Agent 不乱改
+ 如何做到可观测、可回归、可降级
+ 如何监控每个 Agent 的运行状态和执行质量
+ Agent 组最终融合的时候，如何保证质量的？（可能一个 Agent 有问题会导致全盘失败）
+ LangChain + LangGraph
+ Harness底层思想,如何控制 AI 工作
+ 一期使用 DAG，之后升级为多 Agent 共同协作



