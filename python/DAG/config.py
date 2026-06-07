import os


class Config:
    # ---------- API Keys（直接写在本文件，多机运行 git clone 即可，不依赖环境变量 / .env） ----------
    QIANWEN_API_KEY: str = "sk-3d87ca46e5904d5db7af196073d29c8d"
    DEEPSEEK_API_KEY: str = "sk-190f3e034cef42609e94c18179fc5027"
    DOUBAO_API_KEY: str = "ark-8c5b1363-264e-41a5-acab-7217fd0afb78-57e41"
    SERP_API_KEY: str = "e67525d2b6e6635a57fd4dd3fd04df61757652d0bf70ae72117c4a92736cf76d"

    # 各模型的 OpenAI 兼容接入点与默认模型名
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    QIANWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QIANWEN_MODEL: str = "qwen-plus"

    DOUBAO_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    # 豆包(火山方舟)通常需要填「推理接入点 ID」(ep-xxxxxx)
    DOUBAO_MODEL: str = "doubao-lite-32k"

    # 默认 provider 与降级顺序：主 provider 失败时依次尝试备用
    DEFAULT_PROVIDER: str = "deepseek"
    FALLBACK_PROVIDERS = ["deepseek", "qianwen", "doubao"]
    LLM_MAX_RETRIES: int = 2

    # ---------- Langfuse 可观测（云端 US 区域，直接写在本文件） ----------
    LANGFUSE_PUBLIC_KEY: str = "pk-lf-a5fffc02-e041-426a-8c5e-a4d8fbd832c8"
    LANGFUSE_SECRET_KEY: str = "sk-lf-82eba3ff-6f8f-4c66-9087-1e00cbfe0fbb"
    LANGFUSE_HOST: str = "https://us.cloud.langfuse.com"

    # LangGraph checkpoint 持久化文件（SQLite），支持断点续跑
    CHECKPOINT_DB_PATH: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "checkpoints.sqlite"
    )

    # 文章生成模版路径
    ARTICLE_TEMPLATE_PATH: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "Document", "模版", "生成文章的模版.md"
    )
