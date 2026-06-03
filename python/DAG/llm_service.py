import json
import re
from typing import Any, List, Optional
from langchain_openai import ChatOpenAI
from .config import Config


# 模型 provider -> (base_url, model) 的映射，统一管理便于切换
_PROVIDERS = {
    "deepseek": (Config.DEEPSEEK_BASE_URL, Config.DEEPSEEK_MODEL, Config.DEEPSEEK_API_KEY),
    "qianwen": (Config.QIANWEN_BASE_URL, Config.QIANWEN_MODEL, Config.QIANWEN_API_KEY),
    "doubao": (Config.DOUBAO_BASE_URL, Config.DOUBAO_MODEL, Config.DOUBAO_API_KEY),
}


class LLMService:
    """对三家国产大模型做统一封装（均走 OpenAI 兼容接口），支持运行时切换。"""

    def __init__(self, provider: str = "deepseek", temperature: float = 0.7):
        self.temperature = temperature
        self.set_provider(provider)

    def set_provider(self, provider: str):
        if provider not in _PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}. 可选: {list(_PROVIDERS)}")
        self.provider = provider
        base_url, model, api_key = _PROVIDERS[provider]
        self.client = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=self.temperature,
        )

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        messages: List[Any] = []
        if system:
            messages.append(("system", system))
        messages.append(("human", prompt))
        response = self.client.invoke(messages)
        return response.content

    def generate_json(self, prompt: str, system: Optional[str] = None) -> Any:
        """要求模型返回 JSON，并稳健地解析（兼容 ```json 包裹、前后多余文本等情况）。"""
        raw = self.generate(prompt, system=system)
        return self._extract_json(raw)

    @staticmethod
    def _extract_json(text: str) -> Any:
        if text is None:
            return None
        cleaned = text.strip()

        # 去掉 ```json ... ``` / ``` ... ``` 代码块包裹
        fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
        if fence:
            cleaned = fence.group(1).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 兜底：截取第一个 { 或 [ 到最后一个 } 或 ] 之间的内容
        for open_ch, close_ch in (("{", "}"), ("[", "]")):
            start = cleaned.find(open_ch)
            end = cleaned.rfind(close_ch)
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(cleaned[start:end + 1])
                except json.JSONDecodeError:
                    continue
        return None
