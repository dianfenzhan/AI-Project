import importlib.util
import os
from pathlib import Path


def _load_dashscope_api_key() -> str:
    key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if key:
        return key
    # 直接加载 DAG/config.py，避免经 DAG 包 __init__ 引发与 RAG 的循环导入
    try:
        dag_config_path = Path(__file__).resolve().parent.parent / "DAG" / "config.py"
        spec = importlib.util.spec_from_file_location("_dag_config", dag_config_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module.Config, "QIANWEN_API_KEY", "")
    except Exception:
        return ""


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

    # 中英文双语：通义 text-embedding-v4（1024 维），DashScope API
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
    DASHSCOPE_API_KEY: str = _load_dashscope_api_key()
    DASHSCOPE_BASE_URL: str = os.getenv(
        "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/api/v1"
    )
    # 重排使用多语言 cross-encoder（FlashRank MultiBERT，兼容中英文）
    RERANK_MODEL: str = os.getenv("RERANK_MODEL", "ms-marco-MultiBERT-L-12")
    # Milvus/ES 集合名后缀，切换 embedding 后须改后缀并重新入库（避免与旧维度/旧分词混用）
    INDEX_PROFILE: str = os.getenv("INDEX_PROFILE", "v4")

    # 切块：一期用 tiktoken 控制 token 数（而非固定字符数）
    # 512 token ≈ 一个自然段落级语义单元；128 overlap ≈ 25% 重叠，缓解边界截断
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "128"))
    # tiktoken 编码器名（cl100k_base 是 OpenAI 系通用编码，用于估算 token 数）
    TIKTOKEN_ENCODING: str = os.getenv("TIKTOKEN_ENCODING", "cl100k_base")

    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "1024"))
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
