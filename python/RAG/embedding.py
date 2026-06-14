from http import HTTPStatus
import logging
import time
from typing import List, Union

import dashscope
import numpy as np

from .config import Config

logger = logging.getLogger(__name__)

_BATCH_SIZE = 10
_MAX_RETRIES = 2


class EmbeddingService:
    """通义 text-embedding-v4（DashScope API），支持 query/document 非对称检索。"""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or Config.EMBEDDING_MODEL
        self.dimension = Config.EMBEDDING_DIM
        api_key = Config.DASHSCOPE_API_KEY
        if not api_key:
            raise ValueError(
                "DASHSCOPE_API_KEY 未配置：在 DAG/config.py 填写 QIANWEN_API_KEY，"
                "或设置环境变量 DASHSCOPE_API_KEY"
            )
        dashscope.api_key = api_key
        dashscope.base_http_api_url = Config.DASHSCOPE_BASE_URL

    @staticmethod
    def _normalize(vectors: np.ndarray) -> np.ndarray:
        if vectors.ndim == 1:
            norm = float(np.linalg.norm(vectors))
            return vectors / norm if norm > 0 else vectors
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        return vectors / norms

    def _call_api(
        self, inputs: Union[str, List[str]], *, text_type: str
    ) -> List[List[float]]:
        last_err: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = dashscope.TextEmbedding.call(
                    model=self.model_name,
                    input=inputs,
                    dimension=self.dimension,
                    text_type=text_type,
                )
                if resp.status_code != HTTPStatus.OK:
                    raise RuntimeError(
                        f"DashScope embedding 失败: {getattr(resp, 'code', '')} "
                        f"{getattr(resp, 'message', resp)}"
                    )
                items = sorted(
                    resp.output["embeddings"],
                    key=lambda x: x["text_index"],
                )
                vectors = np.array(
                    [item["embedding"] for item in items], dtype=np.float32
                )
                return self._normalize(vectors).tolist()
            except Exception as e:
                last_err = e
                if attempt < _MAX_RETRIES:
                    time.sleep(0.5 * (attempt + 1))
                    logger.warning("Embedding API 重试 %s/%s: %s", attempt + 1, _MAX_RETRIES, e)
                    continue
                raise last_err from e
        raise RuntimeError("Embedding API 调用失败")

    def embed_text(self, text: str, *, is_query: bool = False) -> List[float]:
        text_type = "query" if is_query else "document"
        return self._call_api(text, text_type=text_type)[0]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            all_embeddings.extend(self._call_api(batch, text_type="document"))
        return all_embeddings
