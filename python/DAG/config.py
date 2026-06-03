import os

class Config:
    QIANWEN_API_KEY: str = os.getenv("QIANWEN_API_KEY", "sk-3d87ca46e5904d5db7af196073d29c8d")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "sk-190f3e034cef42609e94c18179fc5027")
    DOUBAO_API_KEY: str = os.getenv("DOUBAO_API_KEY", "ark-8c5b1363-264e-41a5-acab-7217fd0afb78-57e41")
    SERP_API_KEY: str = os.getenv("SERP_API_KEY", "e67525d2b6e6635a57fd4dd3fd04df61757652d0bf70ae72117c4a92736cf76d")

    # 各模型的 OpenAI 兼容接入点与默认模型名（均可用环境变量覆盖）
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    QIANWEN_BASE_URL: str = os.getenv("QIANWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    QIANWEN_MODEL: str = os.getenv("QIANWEN_MODEL", "qwen-plus")

    DOUBAO_BASE_URL: str = os.getenv("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    # 注意：豆包(火山方舟)通常需要填「推理接入点 ID」(ep-xxxxxx)，请用 DOUBAO_MODEL 环境变量覆盖
    DOUBAO_MODEL: str = os.getenv("DOUBAO_MODEL", "doubao-lite-32k")

    # 文章生成模版路径
    ARTICLE_TEMPLATE_PATH: str = os.getenv(
        "ARTICLE_TEMPLATE_PATH",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "Document", "模版", "生成文章的模版.md"),
    )
