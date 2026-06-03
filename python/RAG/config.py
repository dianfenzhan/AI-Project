import os
from typing import Optional

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
    
    QIANWEN_API_KEY: str = os.getenv("QIANWEN_API_KEY", "sk-3d87ca46e5904d5db7af196073d29c8d")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "sk-190f3e034cef42609e94c18179fc5027")
    DOUBAO_API_KEY: str = os.getenv("DOUBAO_API_KEY", "ark-8c5b1363-264e-41a5-acab-7217fd0afb78-57e41")
    
    SERP_API_KEY: str = os.getenv("SERP_API_KEY", "e67525d2b6e6635a57fd4dd3fd04df61757652d0bf70ae72117c4a92736cf76d")
    
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
    # 多语言重排模型，支持中文（原 ms-marco-MiniLM-L-12-v2 仅支持英文）
    RERANK_MODEL: str = os.getenv("RERANK_MODEL", "ms-marco-MultiBERT-L-12")
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 128
    # bge-small-zh-v1.5 输出 512 维
    EMBEDDING_DIM: int = 512
    # 双路召回每一路的候选数
    RECALL_TOP_K: int = 20
    # 重排后最终返回数
    TOP_K: int = 10
    # SerpAPI 抓取的网页数
    TOP_K_SEARCH: int = 5
