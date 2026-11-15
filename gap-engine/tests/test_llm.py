"""LLM provider 与无凭据降级（C-LLM@1/provider）。

全程 patch ``urllib.request.urlopen``，不发起真实外网请求。
"""

from __future__ import annotations

import ast
import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from gap_engine import llm

OK_BODY = json.dumps({"choices": [{"message": {"content": "建议正文"}}]}).encode("utf-8")
ALLOWED_IMPORTS = {"json", "os", "urllib", "dataclasses", "typing"}


class FakeResponse:
    def __init__(self, body: bytes, status: int | None = 200) -> None:
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


def _capture(
    monkeypatch: pytest.MonkeyPatch, body: bytes, status: int | None = 200
) -> list[urllib.request.Request]:
    seen: list[urllib.request.Request] = []

    def fake_urlopen(request: urllib.request.Request, timeout: float | None = None) -> FakeResponse:
        seen.append(request)
        return FakeResponse(body, status)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return seen


def _provider(**overrides: object) -> llm.HttpLlm:
    kwargs: dict[str, object] = {
        "base_url": "https://example.invalid/v1",
        "api_key": "sk-test",
        "model": "m1",
    }
    kwargs.update(overrides)
    return llm.HttpLlm(**kwargs)  # type: ignore[arg-type]


def test_module_imports_only_stdlib_whitelist() -> None:
    roots: set[str] = set()
    source = Path(llm.__file__).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    assert roots <= ALLOWED_IMPORTS


def test_load_provider_without_key_returns_none_and_makes_no_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("无凭据时不得发起请求")

    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    assert llm.load_provider({}) is None
    assert llm.load_provider({llm.ENV_API_KEY: "   "}) is None
    assert llm.load_provider({llm.ENV_API_KEY: ""}) is None


def test_load_provider_defaults() -> None:
    provider = llm.load_provider({llm.ENV_API_KEY: "sk-test"})
    assert provider == llm.HttpLlm(
        base_url=llm.DEFAULT_BASE_URL,
        api_key="sk-test",
        model=llm.DEFAULT_MODEL,
        timeout=llm.DEFAULT_TIMEOUT,
    )
    assert provider.name == "openai-compatible"


def test_load_provider_reads_base_url_and_model() -> None:
    provider = llm.load_provider(
        {
            llm.ENV_API_KEY: "k",
            llm.ENV_BASE_URL: "https://llm.example/v1",
            llm.ENV_MODEL: "custom-model",
        }
    )
    assert provider is not None
    assert provider.base_url == "https://llm.example/v1"
    assert provider.model == "custom-model"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("5", 5.0),
        ("0.5", 0.5),
        ("999", llm.MAX_TIMEOUT),
        ("0", llm.DEFAULT_TIMEOUT),
        ("-3", llm.DEFAULT_TIMEOUT),
        ("abc", llm.DEFAULT_TIMEOUT),
        ("", llm.DEFAULT_TIMEOUT),
    ],
)
def test_load_provider_timeout_is_parsed_and_clamped(raw: str, expected: float) -> None:
    provider = llm.load_provider({llm.ENV_API_KEY: "k", llm.ENV_TIMEOUT: raw})
    assert provider is not None
    assert provider.timeout == expected


def test_load_provider_defaults_to_os_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(llm.ENV_API_KEY, "from-env")
    provider = llm.load_provider()
    assert provider is not None
    assert provider.api_key == "from-env"


def test_complete_success_posts_openai_compatible_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _capture(monkeypatch, OK_BODY)
    assert _provider().complete("你好") == "建议正文"

    (request,) = seen
    assert request.full_url == "https://example.invalid/v1/chat/completions"
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == "Bearer sk-test"
    assert request.get_header("Content-type") == "application/json"
    assert json.loads(request.data.decode("utf-8")) == {
        "model": "m1",
        "messages": [{"role": "user", "content": "你好"}],
        "temperature": 0,
    }


def test_complete_uses_configured_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    timeouts: list[float | None] = []

    def fake_urlopen(
        request: urllib.request.Request, timeout: float | None = None
    ) -> FakeResponse:
        timeouts.append(timeout)
        return FakeResponse(OK_BODY)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    _provider(timeout=7.5).complete("hi")
    assert timeouts == [7.5]


def test_complete_strips_trailing_slash_of_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _capture(monkeypatch, OK_BODY)
    assert _provider(base_url="https://example.invalid/v1/").complete("hi") == "建议正文"
    assert seen[0].full_url == "https://example.invalid/v1/chat/completions"


def test_complete_returns_empty_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(
        request: urllib.request.Request, timeout: float | None = None
    ) -> FakeResponse:
        raise urllib.error.HTTPError(request.full_url, 500, "boom", None, None)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert _provider().complete("hi") == ""


def test_complete_returns_empty_on_non_2xx_status(monkeypatch: pytest.MonkeyPatch) -> None:
    _capture(monkeypatch, OK_BODY, status=500)
    assert _provider().complete("hi") == ""


def test_complete_returns_empty_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(
        request: urllib.request.Request, timeout: float | None = None
    ) -> FakeResponse:
        raise TimeoutError("timed out")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert _provider().complete("hi") == ""


def test_complete_returns_empty_on_url_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(
        request: urllib.request.Request, timeout: float | None = None
    ) -> FakeResponse:
        raise urllib.error.URLError("dns failure")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert _provider().complete("hi") == ""


def test_complete_returns_empty_on_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    _capture(monkeypatch, b"not-json")
    assert _provider().complete("hi") == ""


@pytest.mark.parametrize(
    "body",
    [
        b"{}",
        b'{"choices": []}',
        b'{"choices": [{"message": {}}]}',
        b'{"choices": [{"message": {"content": 42}}]}',
        b'{"choices": [{"message": {"content": null}}]}',
        b"[]",
    ],
)
def test_complete_returns_empty_on_malformed_payload(
    monkeypatch: pytest.MonkeyPatch, body: bytes
) -> None:
    _capture(monkeypatch, body)
    assert _provider().complete("hi") == ""


def test_as_llm_fn_without_provider_returns_none() -> None:
    assert llm.as_llm_fn(None) is None


def test_as_llm_fn_forwards_prompt() -> None:
    prompts: list[str] = []

    class Echo:
        name = "echo"

        def complete(self, prompt: str) -> str:
            prompts.append(prompt)
            return f"echo:{prompt}"

    fn = llm.as_llm_fn(Echo())
    assert fn is not None
    assert fn("需求原文") == "echo:需求原文"
    assert prompts == ["需求原文"]


def test_as_llm_fn_swallows_provider_exception() -> None:
    class Broken:
        name = "broken"

        def complete(self, prompt: str) -> str:
            raise RuntimeError("boom")

    fn = llm.as_llm_fn(Broken())
    assert fn is not None
    assert fn("hi") == ""


def test_as_llm_fn_returns_empty_for_non_string_content() -> None:
    class Weird:
        name = "weird"

        def complete(self, prompt: str) -> str:
            return None  # type: ignore[return-value]

    fn = llm.as_llm_fn(Weird())
    assert fn is not None
    assert fn("hi") == ""