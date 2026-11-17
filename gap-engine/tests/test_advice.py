"""A 段推演建议与两个 CLI 子命令（C-LLM@1/advice + C-LLM@1/cli）。

断言落在 ``render_advice`` 与 CLI 实际写出的文件内容上：无 provider 时产物
只有三行且没有任何条目小节，有 provider 时每个条目小节都带固定标识。
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from gap_engine import cli
from gap_engine.advice import (
    ADVICE_HEADER,
    ADVICE_LIMIT,
    EMPTY_ANSWER_LINE,
    NO_PROVIDER_LINE,
    advice_targets,
    render_advice,
)
from gap_engine.llm import ENV_API_KEY
from gap_engine.pipeline import analyze_spec
from gap_engine.progress import LABEL_ADVICE, ProgressEvent
from gap_engine.schema import Claim, ClaimType, Confidence, Coverage, SearchProbe, Status, Verdict

FIXTURE = Path(__file__).resolve().parents[1] / "contract" / "fixtures" / "fx-spec"


class FakeProvider:
    """鸭子类型 provider：只要求 name 与 complete，不继承 llm 模块的任何类型。"""

    def __init__(self, answer: object = "先补一处并发配置再压测。") -> None:
        self.name = "fake-llm"
        self.answer = answer
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer  # type: ignore[return-value]


def _probe(name: str = "并发原语", scanned: int = 4) -> SearchProbe:
    return SearchProbe(probe=name, target="x", scanned=scanned, hits=0, where=[])


def _claim(
    claim_id: str,
    text: str = "支持 500 并发用户",
    out_of_scope: bool = False,
) -> Claim:
    return Claim(
        id=claim_id,
        text=text,
        source="requirements.md#L4",
        type=ClaimType.concurrency,
        out_of_scope=out_of_scope,
        authority="external",
    )


def _verdict(
    claim_id: str,
    status: Status = Status.no_evidence,
    reason: str = "未找到相关证据；缺口：该补",
) -> Verdict:
    locator = None if status is Status.no_evidence else _locator()
    return Verdict(
        claim_id=claim_id,
        status=status,
        confidence=Confidence.medium,
        locator=locator,
        coverage=Coverage.partial,
        evidence_ids=[],
        reason=reason,
        search_trace=[_probe()],
    )


def _locator():
    from gap_engine.schema import Locator

    return Locator(file="app.py", line=3)


def _analysis(claims, verdicts, repo: str = "fx-spec"):
    return SimpleNamespace(repo=repo, claims=tuple(claims), verdicts=tuple(verdicts))


def _spec_analysis():
    text = (FIXTURE / "requirements.md").read_text(encoding="utf-8")
    return analyze_spec(FIXTURE, text, spec_path="requirements.md")


# ---------- advice_targets ----------


def test_advice_targets_keeps_only_no_evidence_and_in_scope() -> None:
    claims = [
        _claim("c01"),
        _claim("c02", text="提供数据可视化"),
        _claim("c03", out_of_scope=True),
    ]
    verdicts = [
        _verdict("c01"),
        _verdict("c02", status=Status.supported),
        _verdict("c03"),
        _verdict("c99"),
    ]
    targets = advice_targets(_analysis(claims, verdicts))
    assert [claim.id for claim, _ in targets] == ["c01"]


def test_advice_targets_sorted_by_claim_id_and_capped() -> None:
    claims = [_claim(f"c{index:02d}", text=f"需求 {index}") for index in range(12, 0, -1)]
    verdicts = [_verdict(claim.id) for claim in claims]

    targets = advice_targets(_analysis(claims, verdicts))

    assert len(targets) == ADVICE_LIMIT == 10
    assert [claim.id for claim, _ in targets] == [
        "c01",
        "c02",
        "c03",
        "c04",
        "c05",
        "c06",
        "c07",
        "c08",
        "c09",
        "c10",
    ]


def test_advice_targets_on_fixture_picks_two_gaps() -> None:
    targets = advice_targets(_spec_analysis())
    assert [claim.text for claim, _ in targets] == ["支持 500 并发用户", "提供数据可视化"]
    assert all(verdict.locator is None for _, verdict in targets)


# ---------- render_advice ----------


def test_no_provider_artifact_has_exactly_three_non_empty_lines(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "advice.md"

    returned = render_advice(_spec_analysis(), out, None)

    assert returned == out
    text = out.read_text(encoding="utf-8")
    assert [line for line in text.splitlines() if line.strip()] == [
        "# fx-spec 推演建议",
        ADVICE_HEADER,
        NO_PROVIDER_LINE,
    ]
    assert "### " not in text
    assert text.endswith("\n") and not text.endswith("\n\n")


def test_provider_artifact_sections_carry_header(tmp_path: Path) -> None:
    provider = FakeProvider("先补 worker 数，再补压测脚本。")
    out = tmp_path / "advice.md"

    render_advice(_spec_analysis(), out, provider)

    text = out.read_text(encoding="utf-8")
    assert text.startswith("# fx-spec 推演建议\n")
    assert text.count(ADVICE_HEADER) == 3  # 顶部一行 + 两个条目各一行
    assert "### 支持 500 并发用户\n\n" + ADVICE_HEADER + "\n\n先补 worker 数" in text
    assert "### 提供数据可视化\n\n" + ADVICE_HEADER + "\n\n先补 worker 数" in text
    assert NO_PROVIDER_LINE not in text
    assert text.endswith("\n") and not text.endswith("\n\n")
    assert b"\r\n" not in out.read_bytes()
    assert len(provider.calls) == 2


def test_prompt_carries_only_allowed_context(tmp_path: Path) -> None:
    provider = FakeProvider("建议")
    render_advice(_spec_analysis(), tmp_path / "advice.md", provider)

    prompt = provider.calls[0]
    assert "支持 500 并发用户" in prompt
    assert "压测脚本" in prompt and "worker 配置" in prompt
    assert "已扫处数合计：15" in prompt
    assert "缺口标签：该补" in prompt
    for forbidden in (str(FIXTURE), "app.py", "openpyxl", "@app.route", "requirements.md"):
        assert forbidden not in prompt


def test_empty_answer_writes_placeholder(tmp_path: Path) -> None:
    out = tmp_path / "advice.md"
    render_advice(_spec_analysis(), out, FakeProvider("   "))

    text = out.read_text(encoding="utf-8")
    assert text.count(EMPTY_ANSWER_LINE) == 2
    assert "### 支持 500 并发用户" in text


def test_failing_provider_degrades_without_aborting(tmp_path: Path) -> None:
    out = tmp_path / "advice.md"
    render_advice(_spec_analysis(), out, FakeProvider(RuntimeError("boom")))

    text = out.read_text(encoding="utf-8")
    assert text.count(EMPTY_ANSWER_LINE) == 2
    assert text.count(ADVICE_HEADER) == 3


def test_non_string_answer_degrades_to_placeholder(tmp_path: Path) -> None:
    out = tmp_path / "advice.md"
    render_advice(_spec_analysis(), out, FakeProvider(None))

    assert out.read_text(encoding="utf-8").count(EMPTY_ANSWER_LINE) == 2


def test_no_provider_never_calls_provider(tmp_path: Path) -> None:
    provider = FakeProvider()
    render_advice(_spec_analysis(), tmp_path / "advice.md", None)
    assert provider.calls == []


# ---------- gap parse-spec ----------


def test_parse_spec_without_llm_writes_none_provider_and_skips_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    def forbidden() -> None:
        raise AssertionError("未传 --llm 时不得探测凭据")

    monkeypatch.setattr(cli, "load_provider", forbidden)
    out = tmp_path / "spec.json"

    code = cli.main(
        ["parse-spec", str(FIXTURE / "requirements.md"), "--out", str(out)]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == f"spec: {out}"
    assert '"provider": "none"' in out.read_text(encoding="utf-8")


def test_parse_spec_with_llm_and_no_key_degrades_but_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setenv(ENV_API_KEY, "")
    out = tmp_path / "spec.json"

    code = cli.main(
        ["parse-spec", str(FIXTURE / "requirements.md"), "--out", str(out), "--llm"]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert "未配置 GAP_LLM_API_KEY，已降级为规则解析" in captured.err
    assert f"spec: {out}" in captured.out
    assert out.exists()
    assert '"provider": "none"' in out.read_text(encoding="utf-8")


def test_parse_spec_missing_file_returns_two(tmp_path: Path, capsys) -> None:
    out = tmp_path / "spec.json"
    code = cli.main(["parse-spec", str(tmp_path / "nope.md"), "--out", str(out)])

    captured = capsys.readouterr()
    assert code == 2
    assert "spec 文件不存在" in captured.err
    assert not out.exists()


def test_parse_spec_empty_spec_returns_two(tmp_path: Path, capsys) -> None:
    spec = tmp_path / "requirements.md"
    spec.write_text("# 只有标题\n\n没有列表项\n", encoding="utf-8")
    out = tmp_path / "spec.json"

    code = cli.main(["parse-spec", str(spec), "--out", str(out)])

    captured = capsys.readouterr()
    assert code == 2
    assert captured.err.strip() == cli.SPEC_EMPTY_MESSAGE
    assert not out.exists()


def test_parse_spec_requires_out(tmp_path: Path) -> None:
    code = cli.main(["parse-spec", str(FIXTURE / "requirements.md")])
    assert code != 0


# ---------- gap advise ----------


def test_advise_missing_repo_returns_one(tmp_path: Path, capsys) -> None:
    out = tmp_path / "advice.md"
    code = cli.main(
        ["advise", str(tmp_path / "nope"), "--spec", str(FIXTURE / "requirements.md"), "--out", str(out)]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "仓库路径不存在" in captured.err
    assert not out.exists()


def test_advise_missing_spec_returns_two(tmp_path: Path, capsys) -> None:
    out = tmp_path / "advice.md"
    code = cli.main(
        ["advise", str(FIXTURE), "--spec", str(tmp_path / "nope.md"), "--out", str(out)]
    )

    captured = capsys.readouterr()
    assert code == 2
    assert "spec 文件不存在" in captured.err
    assert not out.exists()


def test_advise_empty_spec_returns_two(tmp_path: Path, capsys) -> None:
    spec = tmp_path / "requirements.md"
    spec.write_text("没有列表项\n", encoding="utf-8")
    out = tmp_path / "advice.md"

    code = cli.main(["advise", str(FIXTURE), "--spec", str(spec), "--out", str(out)])

    captured = capsys.readouterr()
    assert code == 2
    assert captured.err.strip() == cli.SPEC_EMPTY_MESSAGE
    assert not out.exists()


def test_advise_with_llm_and_no_key_writes_no_provider_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setenv(ENV_API_KEY, "")
    out = tmp_path / "advice.md"

    code = cli.main(
        [
            "advise",
            str(FIXTURE),
            "--spec",
            str(FIXTURE / "requirements.md"),
            "--out",
            str(out),
            "--llm",
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert "未配置 GAP_LLM_API_KEY，已降级为规则解析" in captured.err
    assert f"advice: {out}" in captured.out
    text = out.read_text(encoding="utf-8")
    assert [line for line in text.splitlines() if line.strip()] == [
        "# fx-spec 推演建议",
        ADVICE_HEADER,
        NO_PROVIDER_LINE,
    ]


def test_advise_without_llm_skips_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden() -> None:
        raise AssertionError("未传 --llm 时不得探测凭据")

    monkeypatch.setattr(cli, "load_provider", forbidden)
    out = tmp_path / "advice.md"

    code = cli.main(
        ["advise", str(FIXTURE), "--spec", str(FIXTURE / "requirements.md"), "--out", str(out)]
    )

    assert code == 0
    assert NO_PROVIDER_LINE in out.read_text(encoding="utf-8")


def test_advise_with_provider_writes_sections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    provider = FakeProvider("先补 worker 数。")
    monkeypatch.setattr(cli, "load_provider", lambda: provider)
    out = tmp_path / "advice.md"
    reports_dir = Path(__file__).resolve().parents[1] / "reports"
    reports_before = {path.name: path.read_bytes() for path in reports_dir.glob("*.md")}

    code = cli.main(
        [
            "advise",
            str(FIXTURE),
            "--spec",
            str(FIXTURE / "requirements.md"),
            "--out",
            str(out),
            "--llm",
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert f"advice: {out}" in captured.out
    text = out.read_text(encoding="utf-8")
    assert "### 支持 500 并发用户" in text
    assert "### 提供数据可视化" in text
    assert text.count(ADVICE_HEADER) == 3
    assert NO_PROVIDER_LINE not in text
    assert len(provider.calls) == 2
    assert {path.name: path.read_bytes() for path in reports_dir.glob("*.md")} == reports_before

# ---------- C-LLM@1/advice@2 progress ----------


def test_render_advice_emits_paired_events_per_model_call(tmp_path: Path) -> None:
    provider = FakeProvider("先补 worker 数。")
    analysis = _spec_analysis()
    total = len(advice_targets(analysis))
    events: list[ProgressEvent] = []

    render_advice(analysis, tmp_path / "advice.md", provider, events.append)

    starts = [event for event in events if event.phase == "start"]
    dones = [event for event in events if event.phase == "done"]
    assert total == 2
    assert len(provider.calls) == len(starts) == len(dones) == total
    assert [event.phase for event in events] == ["start", "done"] * total
    assert [event.index for event in starts] == [1, 2]
    assert all(event.total == total for event in events)
    assert all(event.label == LABEL_ADVICE for event in events)
    assert all(event.seconds == 0.0 for event in starts)


def test_render_advice_without_provider_emits_no_events(tmp_path: Path) -> None:
    events: list[ProgressEvent] = []
    render_advice(_spec_analysis(), tmp_path / "advice.md", None, events.append)
    assert events == []


def test_advice_progress_does_not_change_file_bytes(tmp_path: Path) -> None:
    events: list[ProgressEvent] = []
    plain = render_advice(_spec_analysis(), tmp_path / "plain.md", FakeProvider("补 worker。"))
    marked = render_advice(
        _spec_analysis(), tmp_path / "marked.md", FakeProvider("补 worker。"), events.append
    )

    assert plain.read_bytes() == marked.read_bytes()
    assert events


def test_advise_cli_forced_progress_keeps_stdout_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(cli, "load_provider", lambda: FakeProvider("先补 worker 数。"))
    out = tmp_path / "advice.md"

    code = cli.main(
        [
            "advise",
            str(FIXTURE),
            "--spec",
            str(FIXTURE / "requirements.md"),
            "--out",
            str(out),
            "--llm",
            "--progress",
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == f"advice: {out}"
    assert "[1/2]" in captured.err and "[2/2]" in captured.err
    assert "生成建议" in captured.err


def test_parse_spec_cli_default_progress_silent_on_pipe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(cli, "load_provider", lambda: FakeProvider())
    out = tmp_path / "spec.json"

    code = cli.main(
        ["parse-spec", str(FIXTURE / "requirements.md"), "--out", str(out), "--llm"]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == f"spec: {out}"
    assert "生成判据" not in captured.err