"""symbols 抽取器：主流语言的符号定义行（C-EXTRACTOR@6）。

只认「像符号定义的文本行」，不做 AST 解析、不建立调用图。每个文件至多产出一条证据，
定位粒度是文件内首个符号行——用于让「相关实现」探测项对非 Python 仓库也能产出命中，
而不是只说「扫过 N 处、0 处命中」。
"""

from __future__ import annotations

from ..index import RepoIndex
from ..schema import ClaimType, Evidence, EvidenceKind, Strength
from . import SOURCE_LIMIT, _evidence

SUPPORTS = [ClaimType.feature]

SYMBOL_TOKENS: dict[frozenset[str], tuple[str, ...]] = {
    frozenset({".py"}): ("def ", "class "),
    frozenset({".js", ".jsx", ".ts", ".tsx"}): ("function ", "class ", "export "),
    frozenset({".java", ".cs", ".kt", ".kts", ".scala"}): ("class ", "interface ", "enum "),
    frozenset({".go"}): ("func ", "type "),
    frozenset({".rs"}): ("fn ", "struct ", "impl ", "trait "),
    frozenset({".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx"}): (
        "class ",
        "struct ",
        "namespace ",
        "template ",
    ),
    frozenset({".rb"}): ("def ", "class ", "module "),
    frozenset({".php"}): ("function ", "class ", "interface ", "trait "),
    frozenset({".swift"}): ("func ", "class ", "struct ", "protocol ", "extension "),
}

_SUFFIX_TOKENS: dict[str, tuple[str, ...]] = {
    suffix: tokens for suffixes, tokens in SYMBOL_TOKENS.items() for suffix in suffixes
}


def extract(index: RepoIndex) -> list[Evidence]:
    out: list[Evidence] = []

    for p in index.files:
        tokens = _SUFFIX_TOKENS.get(p.suffix.lower())
        if not tokens:
            continue
        for number, raw in enumerate(index.read(p, limit=SOURCE_LIMIT).splitlines(), start=1):
            if not any(token in raw for token in tokens):
                continue
            out.append(
                _evidence(
                    "symbols",
                    len(out) + 1,
                    EvidenceKind.code,
                    index.rel(p),
                    number,
                    raw.strip(),
                    SUPPORTS,
                    Strength.low,
                )
            )
            break

    return out