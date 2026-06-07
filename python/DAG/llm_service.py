import json
import re
from typing import Any, List, Optional

from langchain_openai import ChatOpenAI
from .config import Config


# 模型 provider -> (base_url, model, api_key) 的映射，统一管理便于切换
_PROVIDERS = {
    "deepseek": (Config.DEEPSEEK_BASE_URL, Config.DEEPSEEK_MODEL, Config.DEEPSEEK_API_KEY),
    "qianwen": (Config.QIANWEN_BASE_URL, Config.QIANWEN_MODEL, Config.QIANWEN_API_KEY),
    "doubao": (Config.DOUBAO_BASE_URL, Config.DOUBAO_MODEL, Config.DOUBAO_API_KEY),
}


class LLMService:
    """对三家国产大模型做统一封装（均走 OpenAI 兼容接口），调用方式完全一致。

    特性：
    - 统一切换：DeepSeek / 通义千问 / 豆包，只换 provider 名，其余调用不变。
    - 失败降级：主 provider 调用失败时，按 Config.FALLBACK_PROVIDERS 依次切换备用模型。
    - 重试：单个 provider 内对偶发错误（限流/网络）重试 Config.LLM_MAX_RETRIES 次。
    - 可观测：generate 支持传入 callbacks（如 Langfuse handler），自动上报调用链。
    """

    def __init__(self, provider: Optional[str] = None, temperature: float = 0.7):
        self.temperature = temperature
        self.provider = provider or Config.DEFAULT_PROVIDER
        if self.provider not in _PROVIDERS:
            raise ValueError(f"Unsupported provider: {self.provider}. 可选: {list(_PROVIDERS)}")

    def _build_client(self, provider: str) -> ChatOpenAI:
        base_url, model, api_key = _PROVIDERS[provider]
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=self.temperature,
        )

    def _provider_chain(self) -> List[str]:
        """主 provider 在前，后接去重后的备用 provider。"""
        chain = [self.provider]
        for p in Config.FALLBACK_PROVIDERS:
            if p in _PROVIDERS and p not in chain:
                chain.append(p)
        return chain

    def generate(self, prompt: str, system: Optional[str] = None, callbacks: Optional[list] = None) -> str:
        messages: List[Any] = []
        if system:
            messages.append(("system", system))
        messages.append(("human", prompt))

        invoke_config = {"callbacks": callbacks} if callbacks else None

        last_error: Optional[Exception] = None
        for provider in self._provider_chain():
            client = self._build_client(provider)
            for attempt in range(Config.LLM_MAX_RETRIES + 1):
                try:
                    response = client.invoke(messages, config=invoke_config)
                    self.provider = provider  # 记录实际生效的 provider
                    return response.content
                except Exception as exc:  # 网络/限流/服务端错误等
                    last_error = exc

        raise RuntimeError(f"所有 LLM provider 调用失败，最后错误：{last_error}")

    def generate_json(self, prompt: str, system: Optional[str] = None, callbacks: Optional[list] = None) -> Any:
        """要求模型返回 JSON，并稳健解析（兼容 ```json 包裹、前后多余文本等情况）。"""
        raw = self.generate(prompt, system=system, callbacks=callbacks)
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
