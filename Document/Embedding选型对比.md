# Embedding 选型对比与决策

> 适用场景：RAG 语义检索、多租户知识库、中英混合文档。  
> 本项目当前选型：**通义 `text-embedding-v4`（1024 维，DashScope API）**。

---

## 一、选型原则（先记住这 5 条）

1. **Embedding 与 LLM 解耦**：检索用哪家向量、生成用哪家大模型，可以不同。豆包生成 + 通义 embedding 完全可行。
2. **语言匹配优先于榜单**：纯英文用英文模型；中英混合用多语言模型；不要用纯英文 small 模型硬扛中文。
3. **API vs 自托管**：API 免 GPU、上线快；自托管（如 bge-m3）适合海量入库、高 QPS、对 API 成本敏感的场景。
4. **换模型 = 换向量空间**：维度可以相同（都是 1024），但向量不可混用，必须 **重建 Milvus 索引 + 全量 re-index**。
5. **用业务集评估，别只看 MTEB**：准备 20～50 条真实 query-doc 对，测 Recall@5 / MRR，比榜单更接近上线效果。

---

## 二、主流模型对比总表

| 模型 | 厂商 | 类型 | 默认维度 | 可调维度 | 单条最大 Token | 批次限制 | 价格（约） | 中文 | 英文 | 跨语言 | 特色能力 |
|------|------|------|----------|----------|----------------|----------|------------|------|------|--------|----------|
| **text-embedding-v4** | 阿里通义 | API | 1024 | 64～2048（8 档） | 8192 | 10 条/次 | ¥0.5/百万 token | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | `text_type` query/doc、sparse、dense&sparse、instruct |
| text-embedding-v3 | 阿里通义 | API | 1024 | 64～1024 | 8192 | 10 条/次 | ¥0.5/百万 token | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 同 v4，能力略弱，新项目优先 v4 |
| **text-embedding-3-small** | OpenAI | API | 1536 | 可缩短 | 8192 | 2048 条/次 | $0.02/百万 token | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 英文性价比之王，OpenAI 生态默认 |
| **text-embedding-3-large** | OpenAI | API | 3072 | 可缩短至 256+ | 8192 | 2048 条/次 | $0.13/百万 token | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 英文精度高，中文非最优 |
| text-embedding-ada-002 | OpenAI | API | 1536 | 不可调 | 8192 | — | $0.10/百万 token | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | _legacy，已被 3-small 替代_ |
| **embedding-3** | 智谱 AI | API | 2048 | 256～2048 | — | 多条 | 按智谱计费 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | OpenAI 兼容 `/embeddings`，国内访问方便 |
| Embedding-V1 / bge 系列 | 百度千帆 | API | 视模型 | 部分固定 | 384～8192 | ≤16 条 | 按千帆计费 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 模型多、需查千帆模型列表选型 |
| doubao-embedding | 火山方舟 | API | 视版本 | 部分可调 | — | VikingDB 集成 | 按火山计费 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 与豆包同生态，多模态 vision 版 |
| **BAAI/bge-m3** | 智源（开源） | 自托管 | 1024 | 固定 | ~8192 | 本地 batch | **免费**（GPU/电费） | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | `prompt_name=query`，本地零 API 费 |
| bge-small-en-v1.5 | 智源（开源） | 自托管 | 384 | 固定 | ~512 | 本地 | 免费 | ❌ | ⭐⭐⭐⭐ | ❌ | 仅纯英文轻量场景 |
| Cohere embed-v4 | Cohere | API | 1536 | 可调 | **128K** | — | $0.12/百万 token | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 长文档、中文强项，海外 API |
| Voyage-3 / 3-large | Voyage AI | API | 1024 | 可调 | 32K | — | $0.06～0.18/百万 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 英文检索强项，代码场景有 voyage-code-3 |

> 价格与维度以各厂商文档为准，上表为 2025～2026 年常见公开报价量级，实际以账单为准。

---

## 三、分厂商说明

### 3.1 OpenAI 系列

| 模型 | 适合 | 不适合 |
|------|------|--------|
| **text-embedding-3-small** | 纯英文 SEO、海外业务、已深度用 OpenAI 生态、追求极低 API 成本 | 中文为主、国内网络不稳定 |
| **text-embedding-3-large** | 英文高精度、金融/法律等语义区分度要求极高的英文库 | 中文知识库首选、预算敏感的大规模入库 |
| ada-002 | 无（存量系统维护） | 新项目 |

**要点：**

- MIRACL 多语言 benchmark 上，3-large（~54.9）优于 3-small（~44.0），但**中文专项仍不如通义 v4 / Cohere / bge-m3**。
- 支持 `dimensions` 参数缩维（如 large 缩到 1024），便于对齐 Milvus 存储。
- 国内访问需考虑代理/合规；LLM 已用国产 API 时，embedding 单独走 OpenAI 会增加一家依赖。

### 3.1.1 专项对比：`text-embedding-3-large` vs 通义 v4 / 3-small / bge-m3

> OpenAI 第三代 embedding 的 **旗舰版**；很多人会和通义 v4 放在一起比较。下面按「能不能用」和「值不值得用」分开说。

#### 基本参数

| 项 | text-embedding-3-large | text-embedding-3-small | text-embedding-v4 | bge-m3 |
|----|------------------------|--------------------------|-------------------|--------|
| 厂商 | OpenAI | OpenAI | 阿里通义 | 智源开源 |
| 部署 | API | API | API | 自托管 |
| 默认维度 | **3072** | 1536 | 1024 | 1024 |
| 可调维度 | ✅ 256～3072（`dimensions` 参数） | ✅ 可缩短 | ✅ 64～2048（8 档） | ❌ 固定 1024 |
| 单条最大 token | 8192 | 8192 | 8192 | ~8192 |
| 批次上限 | 2048 条/次 | 2048 条/次 | 10 条/次 | 本地自定 |
| 价格（约） | **$0.13 / 百万 token** | $0.02 / 百万 token | ¥0.5 / 百万 token | 免费（GPU） |
| Batch 半价 | ✅ | ✅ | ✅（百炼 Batch） | — |
| query/doc 非对称 | ❌ 同一模型编码 | ❌ | ✅ `text_type` | ✅ `prompt_name=query` |
| sparse 混合向量 | ❌ | ❌ | ✅ | ❌（仅 dense） |

#### 公开 Benchmark（参考，不代表你的业务）

| Benchmark | 3-large | 3-small | v4（1024 维） | bge-m3 |
|-----------|---------|---------|---------------|--------|
| MTEB 综合（英文为主） | **~64.6%** | ~62.3% | ~68～71（CMTEB 中文更强） | ~65.5 |
| MIRACL 多语言检索 | **~54.9** | ~44.0 | 多语言优化 | 良好 |
| 中文专项（CMTEB 等） | 中等 | 偏弱 | **强** | 强 |

解读：

- **英文语义检索**：3-large 是 OpenAI 家族最强，MTEB 明显高于 3-small。
- **多语言 / 中文**：MIRACL 上 3-large 不错，但**中文知识库实测**通常仍不如通义 v4、bge-m3、Cohere embed-v4。
- **3072 维 vs 1024 维**：3-large 默认向量是 v4 的 **3 倍存储**；Milvus 索引更大、检索更慢，可用 `dimensions=1024` 缩维，精度会略降。

#### 按场景：3-large 好不好？

| 场景 | 3-large 评价 | 更优选择 |
|------|-------------|----------|
| 纯英文 SEO、出海营销 | ⭐⭐⭐⭐⭐ 首选梯队 | 3-large 或 3-small（看预算） |
| 英文高精度（法律/金融） | ⭐⭐⭐⭐⭐ | 3-large（或缩维到 1536/1024） |
| 中英混合知识库 | ⭐⭐⭐ 能用，非最优 | **通义 v4**、bge-m3 |
| 中文 query 搜英文文档 | ⭐⭐⭐⭐ 跨语言可用 | v4、bge-m3 往往更稳 |
| 国内小公司、LLM 已用千问/豆包 | ⭐⭐ 多一家海外依赖 | **通义 v4** |
| 海量文档反复入库 | ⭐⭐ 成本是 small 的 6.5 倍 | 3-small / bge-m3 / Batch |
| 与豆包生成搭配 | ✅ 技术上完全可行 | 厂商解耦，无硬性要求 |

#### 成本粗算（帮助面试讲清楚）

假设：100 份文档 × 200 chunk × 500 token/chunk = **1000 万 token** 入库一次。

| 模型 | 入库费用（约） | 相对 3-small |
|------|----------------|--------------|
| text-embedding-3-small | $0.20 | 1× |
| **text-embedding-3-large** | **$1.30** | 6.5× |
| text-embedding-v4 | ¥5（约 $0.7） | 3.5× |
| bge-m3 自托管 | 电费/机器 | API 费 ≈ 0 |

检索侧每次 query 仅几十～几百 token，费用可忽略；**入库 + 反复 re-index** 才是 embedding 成本大头。

#### 3-large 的技术特点（面试可讲）

1. **Matryoshka 缩维**：可把 3072 维截断到 1024/512/256，在 MTEB 上仍可能优于 ada-002 全维向量——适合「想要 large 质量、但 Milvus 只想要 1024 维」的场景。
2. **无 query/document 区分**：入库和检索用同一套 API，不像 v4 / BGE 有非对称优化；RAG 里通常靠 **rerank** 补精度。
3. **向量已 L2 归一化**：适合 Milvus **COSINE** 相似度（本项目即如此）。
4. **知识截止**：训练数据有截止日期，对「极新专有名词」不如靠 ES 关键词路 + rerank 兜底。

#### 与本项目选型（通义 v4）的直接对比

| 维度 | text-embedding-3-large | 本项目 text-embedding-v4 | 谁更合适 |
|------|------------------------|--------------------------|----------|
| 中文召回 | 良好 | **更好** | v4 |
| 英文召回 | **更好** | 良好 | 3-large |
| 跨语言（中文搜英文） | 可用 | **更稳** | v4 |
| 国内访问 | 需代理/合规 | **直连** | v4 |
| API Key | 单独 OpenAI | **复用千问 Key** | v4 |
| 与豆包/DeepSeek 共存 | ✅ | ✅ | 平手 |
| 模拟国内生产 | 海外栈 | **国内栈** | v4 |
| 向量存储（默认维） | 3072（12KB/条） | 1024（4KB/条） | v4 更省 |
| 批次入库吞吐 | 2048 条/次 | 10 条/次 | 3-large |

**结论（本项目）**：业务是 **中英混合 + 国内全 API + 千问/豆包生成**，选 **通义 v4** 比 **3-large** 更贴场景。若未来拆出 **纯英文出海线**，可为英文库单独配 **3-small 或 3-large**，与中文库 **分 collection、分 INDEX_PROFILE**，互不干扰。

#### 什么时候该选 3-large？

✅ **推荐选：**

- 客户在美国/欧洲，知识库 **90%+ 英文**
- 已 **全栈 OpenAI**（GPT + embedding + Batch）
- 英文检索 Recall 不够，3-small 提升有限，愿意 **多花 6× API 费** 换精度
- 需要 **2048+ 维** 且想用 OpenAI 生态（缩维到 1024 也可）

❌ **不推荐选：**

- 中文为主或中英混合（优先 v4 / bge-m3）
- 小公司、LLM 已是国产 API（多一家 OpenAI 依赖）
- 预算紧、文档量大、频繁 re-index
- 国内演示/面试要讲「生产架构」——**通义 v4 叙事更顺**

#### 调用示例（OpenAI 兼容）

```python
from openai import OpenAI

client = OpenAI(api_key="sk-...")  # 国内通常需可访问 OpenAI 的网络环境

# 默认 3072 维
resp = client.embeddings.create(
    model="text-embedding-3-large",
    input="how to reduce LLM hallucination",
)

# 缩到 1024 维，对齐 Milvus 配置（与 v4 同维）
resp_1024 = client.embeddings.create(
    model="text-embedding-3-large",
    input="如何减少大模型幻觉",
    dimensions=1024,
)
```

### 3.2 阿里通义（DashScope）

| 模型 | 适合 | 不适合 |
|------|------|--------|
| **text-embedding-v4** | **中英混合 RAG、国内生产、已与千问同账号** | 完全离线、零 API 预算 |
| text-embedding-v3 | v4 不可用时的降级 | 新项目（v4 同价更强） |

**要点：**

- 官方推荐 **1024 维** 作为精度与成本平衡点。
- 检索场景务必区分 **`text_type=query`（检索）** 与 **`text_type=document`（入库）**，类似 BGE 的 query prompt。
- 支持 **dense / sparse / dense&sparse**，可做混合检索（语义 + 关键词），本项目当前仅用 dense。
- 与千问共用 DashScope API Key，工程集成成本最低。

### 3.3 智谱 embedding-3

- OpenAI 兼容 `POST /paas/v4/embeddings`，迁移成本低。
- 维度 256～2048 可调，中文表现良好。
- 适合：**已用智谱 GLM 做生成、希望 embedding 同厂商** 的团队。
- 对比通义 v4：需用业务数据 A/B；通义在中文 RAG 社区案例更多。

### 3.4 百度千帆

- 模型列表多（Embedding-V1、bge-large-zh/ en、tao-8k、Qwen3-Embedding 等），**选型前需先定具体 model id**。
- 适合：**百度云存量客户、政务/企业已采购千帆**。
- 注意：不同模型 **token 上限、批次上限差异大**（如 Embedding-V1 仅 384 token）。

### 3.5 火山方舟 / 豆包 embedding

- `doubao-embedding`：中英双语语义向量，与豆包 LLM 同生态。
- `doubao-embedding-vision`：图文多模态，适合带图知识库。
- 适合：**生成已固定豆包、希望减少厂商数量**；embedding 可通过 VikingDB 或方舟 API 调用。
- 本项目 LLM 已支持豆包，但 embedding 选通义 v4 仍合理（检索与生成解耦）。

### 3.6 开源自托管（BGE 系列）

| 模型 | 适合 | 不适合 |
|------|------|--------|
| **bge-m3** | 海量文档反复 re-index、高 QPS、有 GPU、要零 API 费 | 无运维能力、小团队快速上线 |
| bge-small-en-v1.5 | 纯英文、本地开发机资源极少 | 任何中文场景 |

**要点：**

- bge-m3 与通义 v4 同为 **1024 维多语言**，效果同级，差别在 **部署形态与成本结构**。
- 生产自托管应拆 **独立 Embedding 推理服务**（TEI 等），不要和 FastAPI 同进程抢内存。

---

## 四、按场景选型决策树

```
你的知识库是什么语言？
│
├─ 纯英文
│   ├─ 预算紧、要 API → OpenAI text-embedding-3-small
│   ├─ 要极致英文精度 → OpenAI text-embedding-3-large 或 Voyage-3-large
│   └─ 要零 API 费、可自托管 → bge-small-en-v1.5 / bge-en 系列
│
├─ 中文为主
│   ├─ 国内 API、小公司 → 通义 text-embedding-v4（首选）或 Cohere embed-v4
│   ├─ 已用智谱 GLM → 智谱 embedding-3
│   └─ 已用百度千帆 → 千帆 bge-large-zh / Qwen3-Embedding
│
└─ 中英混合（本项目）
    ├─ API 路线、模拟生产 → 通义 text-embedding-v4（1024 维）✅ 当前选型
    ├─ 生成用豆包、检索也想同厂 → 火山 doubao-embedding（可 A/B）
    ├─ 零 API 费、有 GPU → bge-m3 自托管
    └─ 英文为主但含少量中文 → 仍建议多语言模型，不要用纯英文 small
```

---

## 五、OpenAI vs 国内模型：怎么选（面试话术）

| 维度 | OpenAI embedding | 国内 API（通义/智谱/豆包） | 开源 bge-m3 |
|------|------------------|---------------------------|-------------|
| 国内访问 | 需代理，稳定性看网络 | 直连，延迟低 | 完全本地 |
| 中文召回 | 中等 | 强（通义/Cohere 更强） | 强 |
| 英文召回 | 强 | 良好 | 良好 |
| 成本模型 | 按 token，small 很便宜 | 按 token，v4 约 ¥0.5/M | 一次性 GPU/运维 |
| 与现有栈 | LLM 国产时不一致 | 与千问/豆包易共存 | 与任何 LLM 兼容 |
| 上线速度 | 中 | 快 | 慢（要部署推理） |

**一句话：**

- **出海英文 SEO** → OpenAI 3-small / 3-large  
- **国内中英混合 RAG、小公司全 API** → **通义 text-embedding-v4**  
- **文档量极大、有 GPU** → bge-m3 自托管  

---

## 六、本项目最终选型与理由

### 选定方案

```
Embedding：通义 text-embedding-v4（1024 维，DashScope API）
入库：text_type=document
检索：text_type=query
重排：ms-marco-MultiBERT-L-12（FlashRank，本地）
向量库：Milvus（COSINE）+ Elasticsearch（全文）
索引后缀：INDEX_PROFILE=v4
LLM：DeepSeek / 千问 / 豆包（与 embedding 厂商无关）
```

### 为什么不是 OpenAI（含 text-embedding-3-large）？

1. 业务是 **中英混合**，通义 v4 中文与跨语言检索更稳；3-large 英文强，但中文专项不如 v4。  
2. LLM 已走 **国产 API**，embedding 也用 DashScope，**一家 Key、国内直连**；3-large 多一家 OpenAI 依赖且国内网络不稳。  
3. **成本**：3-large（$0.13/M）是 3-small 的 6.5 倍，入库百万 token 量级时差距明显；v4 约 ¥0.5/M，且与千问同账单。  
4. **工程**：3-large 默认 3072 维，存储是 v4（1024 维）的 3 倍；虽可 `dimensions=1024` 缩维，但无 `text_type` 非对称检索。  
5. 若未来做 **纯英文出海子产品**，可为英文库单独上 **3-small / 3-large**，与中文库分索引，见 §3.1.1。

### 为什么不是 bge-m3 自托管？

1. 目标是 **模拟生产**：生产小公司通常 **不买 GPU 跑 embedding**。  
2. 本地 bge-m3 适合开发调试；演示/面试场景用 **API 版** 叙事更一致。  
3. 若日后文档量极大、API 费成为瓶颈，可再评估 **bge-m3 独立推理服务**。

### 为什么不是豆包 embedding？

- 完全可行，尤其生成已用豆包时。  
- 选通义 v4 的原因：**中文 RAG 案例与文档更成熟**、`text_type` / sparse 能力更完整；与千问 Key 复用最简单。  
- 若团队 **全栈火山**，建议用 doubao-embedding 做 A/B 再定。

---

## 七、配套组件选型（Embedding 不够，还要 Rerank）

| 场景 | 推荐 Rerank |
|------|-------------|
| 纯英文 | `ms-marco-MiniLM-L-12-v2`（FlashRank） |
| 中英混合（本项目） | `ms-marco-MultiBERT-L-12`（FlashRank） |
| 国内 API 一体化 | 通义 rerank API 或 `bge-reranker-v2-m3` |

Rerank 只对 RRF 后的 **几十条候选** 做 cross-encoder 精排，延迟可控，**生产不建议省略**。

---

## 八、评估与迁移 checklist

### 上线前评估

- [ ] 准备 20～50 条业务 query（中英各半）  
- [ ] 标注正确 doc chunk，算 Recall@5 / Recall@10  
- [ ] 对比至少 2 个候选（如 v4 vs bge-m3 或 v4 vs OpenAI small）  
- [ ] 测 P95 延迟：入库 100 chunk、单次检索各需多久  

### 切换 embedding 时

- [ ] 修改 `EMBEDDING_MODEL`、`EMBEDDING_DIM`、`INDEX_PROFILE`  
- [ ] 重建 Milvus collection（维度/向量空间变化）  
- [ ] 全量 re-index 文档  
- [ ] ES 索引可保留或重建（全文路与 embedding 无关，但建议新后缀保持一致）  
- [ ] 更新 query 侧编码逻辑（`text_type=query` 或 BGE prompt）  

---

## 九、参考链接

- [OpenAI Embeddings 指南](https://platform.openai.com/docs/guides/embeddings)
- [通义向量化模型说明（百炼）](https://help.aliyun.com/zh/model-studio/model-introduction-6)
- [智谱 Embedding-3](https://docs.bigmodel.cn/cn/guide/models/embedding/embedding-3)
- [百度千帆 Embedding API](https://cloud.baidu.com/doc/qianfan-api/s/Fm7u3ropn)
- [火山 VikingDB Embedding](https://www.volcengine.com/docs/84313/1254554)
- [BGE-M3（HuggingFace）](https://huggingface.co/BAAI/bge-m3)

---

## 十、结论卡片（可打印 / 面试前扫一眼）

| 问题 | 答案 |
|------|------|
| 纯英文 SEO？ | OpenAI **text-embedding-3-small** |
| 纯英文、要最高精度？ | OpenAI **text-embedding-3-large**（可缩维到 1024） |
| 中英混合、国内 API？ | 通义 **text-embedding-v4**（1024 维） |
| 3-large 和 v4 怎么选？ | 英文为主 → 3-large；中英混合/国内 → **v4**（见 §3.1.1） |
| 中文最强、预算够？ | 通义 v4 或 **Cohere embed-v4** |
| 零 API 费、有 GPU？ | **bge-m3** 自托管 |
| 能和豆包一起用吗？ | **能**，3-large / v4 都与 LLM 解耦 |
| 本项目用什么？ | **text-embedding-v4 + MultiBERT rerank** |
