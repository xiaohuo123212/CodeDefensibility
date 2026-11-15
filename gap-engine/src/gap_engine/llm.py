"""OpenAI 兼容的 LLM provider 与无凭据降级（C-LLM@1/provider）。

零第三方依赖：只用 ``urllib.request`` 发请求。``complete`` 的任何失败
（网络、非 2xx、非法 JSON、结构缺字段）都降级为空串，不抛异常、不重试，
以免打断对账主链路。
"""

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Mapping, Protocol

ENV_BASE_URL = "GAP_LLM_BASE_URL"
ENV_API_KEY = "GAP_LLM_API_KEY"
ENV_MODEL = "GAP_LLM_MODEL"
ENV_TIMEOUT = "GAP_LLM_TIMEOUT"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT = 30.0
MAX_TIMEOUT = 120.0

__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_MODEL",
    "DEFAULT_TIMEOUT",
    "ENV_API_KEY",
    "ENV_BASE_URL",
    "ENV_MODEL",
    "ENV_TIMEOUT",
    "MAX_TIMEOUT",
    "HttpLlm",
    "LlmProvider",
    "as_llm_fn",
    "load_provider",
]


class LlmProvider(Protocol):
    name: str

    def complete(self, prompt: str) -> str: ...


@dataclass(frozen=True)
class HttpLlm:
    base_url: str
    api_key: str
    model: str
    timeout: float = DEFAULT_TIMEOUT
    name: str = "openai-compatible"

    def complete(self, prompt: str) -> str:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        body = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                status = getattr(response, "status", 200)
                if status is not None and not (200 <= int(status) < 300):
                    return ""
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, TypeError, ValueError):
            # HTTPError/socket.timeout 落在 URLError/OSError，JSONDecodeError 落在 ValueError。
            return ""
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return ""
        return content if isinstance(content, str) else ""


def _timeout_of(env: Mapping[str, str]) -> float:
    raw = (env.get(ENV_TIMEOUT) or "").strip()
    if not raw:
        return DEFAULT_TIMEOUT
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_TIMEOUT
    if value <= 0:
        # 解析成功但落在 (0, MAX_TIMEOUT] 之外时取默认值，保证下界始终为正。
        return DEFAULT_TIMEOUT
    return min(value, MAX_TIMEOUT)


def load_provider(env: Mapping[str, str] | None = None) -> LlmProvider | None:
    source = os.environ if env is None else env
    api_key = (source.get(ENV_API_KEY) or "").strip()
    if not api_key:
        return None
    base_url = (source.get(ENV_BASE_URL) or "").strip() or DEFAULT_BASE_URL
    model = (source.get(ENV_MODEL) or "").strip() or DEFAULT_MODEL
    return HttpLlm(
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout=_timeout_of(source),
    )


def as_llm_fn(provider: LlmProvider | None) -> Callable[[str], str] | None:
    if provider is None:
        return None

    def complete(prompt: str) -> str:
        try:
            text = provider.complete(prompt)
        except Exception:  # provider 属外部边界，任何异常都降级为空串
            return ""
        return text if isinstance(text, str) else ""

    return complete