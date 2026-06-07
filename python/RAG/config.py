import os


class Config:
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
    ES_HOST: str = os.getenv("ES_HOST", "localhost")
    ES_PORT: int = int(os.getenv("ES_PORT", "9200"))
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "example_db")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "admin")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "password")

    # 业务以英文出海内容为主，embedding 使用英文模型；bge-small-en-v1.5 输出 384 维
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    # 重排使用英文 cross-encoder（FlashRank 英文模型）
    RERANK_MODEL: str = os.getenv("RERANK_MODEL", "ms-marco-MiniLM-L-12-v2")

    # 切块：一期用 tiktoken 控制 token 数（而非固定字符数）
    # 512 token ≈ 一个自然段落级语义单元；128 overlap ≈ 25% 重叠，缓解边界截断
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "128"))
    # tiktoken 编码器名（cl100k_base 是 OpenAI 系通用编码，用于估算 token 数）
    TIKTOKEN_ENCODING: str = os.getenv("TIKTOKEN_ENCODING", "cl100k_base")

    # bge-small-en-v1.5 输出 384 维
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "384"))
    # 双路召回每一路的候选数
    RECALL_TOP_K: int = int(os.getenv("RECALL_TOP_K", "20"))
    # 重排后最终返回数
    TOP_K: int = int(os.getenv("TOP_K", "10"))
    # SerpAPI 抓取的网页数
    TOP_K_SEARCH: int = int(os.getenv("TOP_K_SEARCH", "5"))

    # RRF（Reciprocal Rank Fusion）融合参数：score = Σ 1 / (RRF_K + rank)
    # rank 从 1 开始；K 越大，排名靠前的优势越平滑，常用 60
    RRF_K: int = int(os.getenv("RRF_K", "60"))

    # 文档两级权限：系统级（所有租户可见）用固定 tenant 标识；租户级用各自 tenant_id
    SYSTEM_TENANT_ID: str = os.getenv("SYSTEM_TENANT_ID", "__system__")
    SCOPE_SYSTEM: str = "system"
    SCOPE_TENANT: str = "tenant"
