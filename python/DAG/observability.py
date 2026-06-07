"""Langfuse 可观测接入（云端，可选）。

配置来源：直接读取 DAG/config.py 中的 LANGFUSE_* 常量，不依赖环境变量或 .env 文件。
未配置 key（为空字符串）时自动跳过，不影响服务运行。
"""
from typing import Optional

from .config import Config


def is_enabled() -> bool:
    return bool(Config.LANGFUSE_PUBLIC_KEY and Config.LANGFUSE_SECRET_KEY)


def get_langfuse_handler(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tags: Optional[list] = None,
):
    """返回一个 Langfuse CallbackHandler；不可用时返回 None。

    把它作为 callback 传给 LangChain/LangGraph 调用，即可自动上报：
    prompt、模型、token、耗时、成本、调用链等。
    """
    if not is_enabled():
        return None

    try:
        from langfuse.callback import CallbackHandler
    except ImportError:
        return None

    try:
        return CallbackHandler(
            public_key=Config.LANGFUSE_PUBLIC_KEY,
            secret_key=Config.LANGFUSE_SECRET_KEY,
            host=Config.LANGFUSE_HOST,
            session_id=session_id,
            user_id=user_id,
            tags=tags or [],
        )
    except Exception:
        # 任意初始化异常都不应阻断主流程
        return None
