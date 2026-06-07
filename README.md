# SEO RAG Platform

基于 Java + Python 的 SEO 内容生成平台，实现 RAG 知识库、双路召回、AI 工作流等功能。

## 技术栈

### 后端
- Java 17 + Spring Boot 3.5
- Python 3.x + FastAPI + LangChain + LangGraph
- PostgreSQL（租户管理）
- Milvus（向量存储）
- Elasticsearch（全文检索）
- Docker Compose（服务编排）

### 前端
- Vue 3 + Element Plus + Vite

### AI
- DeepSeek / 通义千问 / 豆包（可切换）
- Sentence-Transformers（向量化）
- FlashRank（重排序）
- SerpAPI（Google 搜索）

## 项目结构

```
.
├── java/                     # Java Spring Boot 后端
│   ├── pom.xml
│   └── src/
├── python/                   # Python FastAPI + RAG/DAG 服务
│   ├── api_server.py
│   ├── requirements.txt
│   ├── RAG/
│   └── DAG/
├── frontend/                 # Vue 3 前端
│   └── src/
│       ├── views/
│       └── router/
└── docker-compose.yml        # PostgreSQL + Milvus + ES + Kibana
```

## 快速开始

### 启动顺序

建议按下面顺序启动：先启动数据库和检索组件，再启动 Python RAG/DAG 服务，然后启动 Java 网关，最后启动 Vue 前端。

#### 1. 启动基础服务（PostgreSQL + Milvus + Elasticsearch + Kibana）

```bash
docker compose up -d
```

#### 2. 安装 Python 依赖

需要 **Python 3.11+**（推荐 Homebrew 安装：`brew install python@3.11`）。在 `python/` 目录下创建虚拟环境并安装依赖：

```bash
cd /path/to/Project-Self/python
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

首次安装会下载 `sentence-transformers`、`flashrank` 等较大依赖（含 PyTorch），可能需要几分钟。

若提示 `No module named pip`，先执行 `python3 -m ensurepip --upgrade`；若仍失败，可重装 Python：`brew reinstall python@3.11`。

#### 3. 启动 Python API 服务

必须在 `python/` 目录下启动（代码使用 `from RAG import ...` 相对导入）：

```bash
cd /path/to/Project-Self/python
source .venv/bin/activate   # 新终端需要先激活虚拟环境
python3 api_server.py
```

#### 4. 启动 Java 后端

新开一个终端：

```bash
cd java
mvn spring-boot:run
```

#### 5. 启动前端

新开一个终端：

```bash
cd frontend
npm install
npm run dev
```

### 访问地址

- 前端 UI: `http://localhost:5173/seo-frontend`
- Java 后端: `http://localhost:8080/seo-java`
- Python API: `http://localhost:8000/seo-python`
- Elasticsearch: `http://localhost:9200/seo-elasticsearch`
- Kibana: `http://localhost:5601/seo-kibana`
- Milvus: `localhost:19530/seo-milvus`
- PostgreSQL: `localhost:5432/seo-postgres`

### API 文档（Swagger）

| 服务 | Swagger UI | OpenAPI JSON |
|------|-----------|--------------|
| Java 网关 | `http://localhost:8080/seo-java/swagger-ui/index.html` | `http://localhost:8080/seo-java/v3/api-docs` |
| Python RAG/DAG | `http://localhost:8000/seo-python/docs` | `http://localhost:8000/seo-python/openapi.json` |

Python 服务还提供 ReDoc 文档：`http://localhost:8000/seo-python/redoc`

### 推荐验证流程

启动完成后，建议按下面流程验证阶段一功能：

1. 打开前端 UI: `http://localhost:5173`
2. 进入「文档上传」页面，填写 `tenantId` 和 `collectionName`，上传 PDF / MD / TXT / DOCX 文档
3. 进入「知识库搜索」页面，用同一个 `tenantId` 和 `collectionName` 搜索刚上传文档中的内容
4. 进入「文章生成」页面，填写主题、关键词、租户 ID、集合名称，选择 AI 模型
5. 点击「第一步：生成标题」，从 5 个标题中选择一个
6. 点击「第二步：生成大纲」，从 3 套大纲中选择一套
7. 点击「第三步：生成文章」，检查文章是否基于知识库和 SerpAPI 搜索结果生成

### 停止服务

停止 Docker 基础服务：

```bash
docker compose down
```

Python API、Java 后端、前端开发服务在各自终端按 `Ctrl+C` 停止。

## 功能说明

### 1. 文档上传与索引
- 支持 PDF、MD、TXT、DOCX 格式
- 语义切块（512 字符左右，128 overlap）
- 向量化存储到 Milvus
- 全文索引到 Elasticsearch
- 租户隔离

### 2. 双路召回与重排序
- 向量检索（Milvus）
- 全文检索（Elasticsearch）
- Query 改写 + 多查询召回，提升召回覆盖率
- FlashRank 重排序
- Top 10 结果返回

### 3. SerpAPI 搜索
- Google 搜索相关内容
- 自动抓取网页内容
- 集成到 RAG 上下文

### 4. SEO 文章生成 DAG
- 基于 RAG + SerpAPI 生成 5 个标题
- 选择标题后生成 3 套大纲
- 根据选定大纲生成完整文章
- 可切换 AI 模型（DeepSeek / 通义千问 / 豆包）
- 使用 LangGraph 中断恢复（human-in-the-loop）实现三步交互

### 5. RAG 质量与溯源
- 文章生成后返回 `quality_report`，评估忠实度、相关性、结构性和引用覆盖率
- 返回 `citations`，可追溯到知识库 chunk 或网页搜索结果
- 前端生成页展示 query 改写结果、质量评分、风险建议和引用来源

## API 接口

### Java 后端 (8080端口)
- `POST /api/v1/upload` - 上传文档
- `POST /api/v1/search` - 搜索知识库
- `POST /api/v1/generate/titles` - 第一步：生成 5 个标题
- `POST /api/v1/generate/outlines` - 第二步：基于选中标题生成 3 套大纲
- `POST /api/v1/generate/article` - 第三步：基于选中大纲生成文章
- `POST /api/v1/tenants` - 创建租户

### Python 后端 (8000端口)
- `POST /api/upload` - 文档处理与索引
- `POST /api/search` - 双路召回搜索
- `POST /api/generate/titles` - 第一阶段生成标题（返回 thread_id）
- `POST /api/generate/outlines` - 第二阶段生成大纲（需传 thread_id + selected_title）
- `POST /api/generate/article` - 第三阶段生成文章，并返回质量评估和引用来源（需传 thread_id + selected_outline）

### 前端 (5173端口)
- `/upload` - 文档上传页面
- `/search` - 知识库搜索页面
- `/generate` - 文章生成页面

## 配置说明

API 密钥已配置在代码中，可通过环境变量覆盖：
- `DEEPSEEK_API_KEY`
- `QIANWEN_API_KEY`
- `DOUBAO_API_KEY`
- `SERP_API_KEY`
- `DOUBAO_MODEL`（建议配置为方舟推理接入点 ID，例如 `ep-xxxxxx`）
- `RERANK_MODEL`（默认 `ms-marco-MultiBERT-L-12`）

## 注意事项

1. 所有服务的重启策略设置为 `no`，重启电脑后不会自动启动
2. 租户隔离通过 `tenant_id` 和 `collection_name` 实现
3. 首次启动需要下载相关 AI 模型
4. 依赖中 SerpAPI 对应包为 `google-search-results`
