"""固定探测计划与搜索轨迹（C-PROBER@1/@2/@3/@4/@5）。

每条声称都跑一遍固定计划：即使一个都没命中，也留下 ``SearchProbe``，
让报告的 audit effort 可被对手复核。``where_contains`` 让每个探测项只报告
它真正在找的那类证据；``path_only`` 用于"某类文件在不在仓库里"这类探测项，
只看路径、不看文件内文本；feature 类还要按需求关键词再收窄，避免不同功能
需求报出同一批命中。第 2 轮起改用 ``ALTERNATE_PLANS`` 里的换假设计划（表驱动、可枚举）。
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch

from .extractors import EXTRACTORS
from .index import RepoIndex
from .matcher import feature_terms
from .schema import Claim, ClaimType, Evidence, SearchProbe


@dataclass(frozen=True)
class ProbeSpec:
    probe: str
    extractor: str
    target: str
    where_contains: tuple[str, ...] = ()
    path_only: bool = False


_BENCH_TOKENS: tuple[str, ...] = ("locust", "k6", "wrk", "ab", "jmeter", "benchmark")
_CONCURRENCY_TOKENS: tuple[str, ...] = (
    "threaded",
    "async def",
    "ThreadPool",
    "Lock(",
    "Semaphore",
    "gather",
)

_SHARED_SPECS: tuple[ProbeSpec, ...] = (
    ProbeSpec("结构指标", "structure", "文件规模与模块划分"),
    ProbeSpec("依赖", "deps", "第三方依赖声明"),
    ProbeSpec("配置", "config", "部署与运行配置"),
    ProbeSpec("入口", "entry", "启动入口"),
)

PLAN: dict[ClaimType, tuple[ProbeSpec, ...]] = {
    ClaimType.performance: (
        ProbeSpec("压测脚本", "bench", "locust/k6/wrk/ab 压测脚本", _BENCH_TOKENS),
        ProbeSpec("压测结果", "bench", "压测结果与容量报告", ("result", "report", "csv", "bench")),
        ProbeSpec(
            "连接池/缓存配置",
            "config",
            "pool_size/max_connections/缓存配置",
            ("pool", "cache", "workers", "max_connections"),
        ),
        ProbeSpec("并发原语", "concurrency", "线程/协程/锁等并发原语", _CONCURRENCY_TOKENS),
    ),
    ClaimType.concurrency: (
        ProbeSpec("压测脚本", "bench", "locust/k6/wrk/ab 压测脚本", _BENCH_TOKENS),
        ProbeSpec("并发原语", "concurrency", "线程/协程/锁等并发原语", _CONCURRENCY_TOKENS),
        ProbeSpec(
            "worker 配置",
            "config",
            "workers 进程数配置",
            ("workers", "worker_class", "gunicorn", "uvicorn"),
        ),
        ProbeSpec(
            "连接池",
            "config",
            "pool_size/max_connections 配置",
            ("pool", "max_connections", "connection", "cache"),
        ),
    ),
    ClaimType.feature: (
        ProbeSpec(
            "路由/入口",
            "entry",
            "路由与启动入口",
            ("route", "@app.", "@router", "__main__", "main("),
        ),
        ProbeSpec(
            "依赖声明",
            "deps",
            "依赖清单中的相关库",
            ("requirements", "pyproject.toml", "package.json"),
            path_only=True,
        ),
        ProbeSpec("相关实现", "structure", "按模块划分的实现文件", ("def ", "class ")),
        ProbeSpec("测试覆盖", "tests", "对应测试文件", ("test_", "_test.")),
    ),
    ClaimType.testing: (
        ProbeSpec("测试文件", "tests", "test_*.py 等测试文件", ("test_", "_test.", "spec.")),
        ProbeSpec(
            "测试配置",
            "tests",
            "pytest/coverage 配置",
            ("pyproject.toml", "setup.cfg", "tox.ini", "pytest.ini", ".coveragerc", "package.json"),
            path_only=True,
        ),
        ProbeSpec(
            "覆盖率报告",
            "tests",
            "coverage.xml/.coverage/htmlcov 产物",
            (".coverage", "coverage.xml", "coverage.json", "coverage.csv", "htmlcov"),
            path_only=True,
        ),
        ProbeSpec(
            "CI 配置",
            "config",
            "CI 与流水线配置",
            (".github", ".gitlab-ci", "Jenkinsfile", ".travis", "azure-pipelines"),
            path_only=True,
        ),
    ),
    ClaimType.architecture: _SHARED_SPECS,
    ClaimType.scale: _SHARED_SPECS,
    ClaimType.security: _SHARED_SPECS,
}

_ARTIFACT_SPEC = ProbeSpec("压测结果文件", "artifact", "结果/产物文件里的测量痕迹")
_COVERAGE_ARTIFACT_SPEC = ProbeSpec("覆盖率产物", "artifact", "coverage.xml 等覆盖率产物文件")

# 第 2 轮起的换假设计划：每类只列真实有效的假设，不为凑轮数而凑。
# 其余类型没有第 2 轮，总轮数恒为 1（C-PROBER@5）。
ALTERNATE_PLANS: dict[ClaimType, tuple[ProbeSpec, ...]] = {
    ClaimType.performance: (_ARTIFACT_SPEC,),
    ClaimType.concurrency: (_ARTIFACT_SPEC,),
    ClaimType.testing: (_COVERAGE_ARTIFACT_SPEC,),
}

# extractor → 关注的文件后缀/模式（用于 scanned 计数，语义是"查过几处文件"）。
CANDIDATE_FILES: dict[str, str] = {
    "bench": "*.py,*.js,*.sh,*.yml",
    "tests": "test_*.py,*_test.py,*.toml",
    "concurrency": "*.py,*.js,*.conf",
    "config": "*",  # config 抽取器对全库做文件名线索匹配（gunicorn.conf.py / Dockerfile 不看后缀）
    "deps": "requirements*.txt,pyproject.toml,package.json",
    "entry": "*.py,*.js",
    "structure": "*",
    "artifact": "*.log,*.csv,*.json,*.txt,*.xml,*.html",
}


def plan(claim: Claim, round: int = 1) -> tuple[ProbeSpec, ...]:
    if round <= 1:
        return PLAN[claim.type]
    alternates = ALTERNATE_PLANS.get(claim.type, ())
    index = round - 2
    return (alternates[index],) if index < len(alternates) else ()


def scanned_count(extractor: str, index: RepoIndex) -> int:
    patterns = [p.strip() for p in CANDIDATE_FILES.get(extractor, "*").split(",") if p.strip()]
    count = 0
    for path in index.files:
        name = path.name
        rel = index.rel(path)
        if any(fnmatch(name, pattern) or fnmatch(rel, pattern) for pattern in patterns):
            count += 1
    return count


def run(
    claim: Claim, index: RepoIndex, round: int = 1
) -> tuple[list[SearchProbe], list[Evidence]]:
    probes: list[SearchProbe] = []
    evidence: list[Evidence] = []
    seen_ids: set[str] = set()

    for spec in plan(claim, round):
        raw_items: list[Evidence] = []
        scanned = 0
        extractor = EXTRACTORS.get(spec.extractor)
        if extractor is not None:
            try:
                raw_items = list(extractor(index))
            except Exception:  # 单个抽取器失败不得中断整条声称的探测
                raw_items = []
            else:
                scanned = scanned_count(spec.extractor, index)

        items = raw_items
        if spec.where_contains:
            items = []
            for item in raw_items:
                haystack = item.file if spec.path_only else f"{item.file} {item.snippet}"
                if any(token in haystack for token in spec.where_contains):
                    items.append(item)

        # 类级过滤只区分"路由/依赖"这类，feature 还需按需求关键词收窄，
        # 否则「可视化」与「登录」会报出同一批命中，与 no_evidence 结论冲突。
        if claim.type is ClaimType.feature:
            terms = feature_terms(claim.text)
            if terms:
                items = [item for item in items if any(t in f"{item.file} {item.snippet}".lower() for t in terms)]

        hits = [item for item in items if claim.type in item.supports]
        where: list[str] = []
        for item in hits:
            locator = f"{item.file}:{item.line}"
            if locator not in where:
                where.append(locator)

        probes.append(
            SearchProbe(
                probe=spec.probe,
                target=spec.target,
                scanned=max(scanned, len(hits)),
                hits=len(hits),
                where=where[:5],
            )
        )
        for item in raw_items:
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                evidence.append(item)

    return probes, evidence