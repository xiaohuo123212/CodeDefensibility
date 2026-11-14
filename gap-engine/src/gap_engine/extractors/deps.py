"""deps 抽取器：requirements*.txt / pyproject.toml / package.json 声明的依赖名。"""

from __future__ import annotations

import json
import re
import tomllib

from ..index import RepoIndex
from ..schema import ClaimType, Evidence, EvidenceKind, Strength
from . import SOURCE_LIMIT, _evidence, _line_text

DEP_CAP = 40
SUPPORTS = [ClaimType.feature]
_NAME_SPLIT = re.compile(r"[<>=!~;\[\s,]")


def _requirement_name(raw: str) -> str | None:
    line = raw.split("#", 1)[0].strip()
    if not line or line.startswith("-"):
        return None
    if line.startswith(("http://", "https://", "git+", "file:", ".", "/")):
        return None
    name = _NAME_SPLIT.split(line, maxsplit=1)[0].strip()
    return name or None


def _requirements_names(text: str) -> list[str]:
    names: list[str] = []
    for raw in text.splitlines():
        name = _requirement_name(raw)
        if name:
            names.append(name)
    return names


def _pyproject_names(text: str) -> list[str]:
    try:
        data = tomllib.loads(text)
    except (tomllib.TOMLDecodeError, ValueError):
        return [
            name
            for raw in text.splitlines()
            if '"' in raw and (name := _requirement_name(raw.strip().strip('",')))
        ]

    names: list[str] = []
    project = data.get("project", {}) or {}
    for item in project.get("dependencies", []) or []:
        name = _requirement_name(str(item))
        if name:
            names.append(name)
    for group in (project.get("optional-dependencies", {}) or {}).values():
        for item in group or []:
            name = _requirement_name(str(item))
            if name:
                names.append(name)

    poetry = (data.get("tool", {}) or {}).get("poetry", {}) or {}
    for key in ("dependencies", "dev-dependencies"):
        names.extend((poetry.get(key) or {}).keys())
    for group in (poetry.get("group") or {}).values():
        names.extend(((group or {}).get("dependencies") or {}).keys())
    return names


def _package_names(text: str) -> list[str]:
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    names = list((data.get("dependencies") or {}).keys())
    names.extend((data.get("devDependencies") or {}).keys())
    return names


def extract(index: RepoIndex) -> list[Evidence]:
    out: list[Evidence] = []
    seen: set[str] = set()

    for p in index.files:
        name = p.name.lower()
        text = index.read(p, limit=SOURCE_LIMIT)
        if name.startswith("requirements") and name.endswith(".txt"):
            names = _requirements_names(text)
        elif name == "pyproject.toml":
            names = _pyproject_names(text)
        elif name == "package.json":
            names = _package_names(text)
        else:
            continue

        for dep in names:
            key = dep.lower()
            if not key or key in seen:
                continue
            line = index.line_of(p, dep)
            if line is None:
                continue
            snippet = _line_text(index, p, line)
            if not snippet:
                continue
            seen.add(key)
            if len(out) >= DEP_CAP:
                return out
            out.append(
                _evidence(
                    "deps",
                    len(out) + 1,
                    EvidenceKind.dep,
                    index.rel(p),
                    line,
                    snippet,
                    SUPPORTS,
                    Strength.medium,
                )
            )

    return out