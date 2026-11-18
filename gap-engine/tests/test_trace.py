"""C-TRACE@1/@2：轨迹统计、去重保序、去重扫描数与空输入。"""

import pytest

from gap_engine.schema import SearchProbe
from gap_engine.trace import TraceSummary, distinct_scanned, headline, summarize


def test_summarize_counts():
    trace = [
        SearchProbe(probe="threaded", target="app.run", scanned=3, hits=1, where=["app.py"]),
        SearchProbe(probe="workers", target="gunicorn", scanned=5, hits=2, where=["gunicorn.conf.py"]),
        SearchProbe(probe="locust", target="bench", scanned=2, hits=0, where=["."]),
    ]
    summary = summarize(trace)
    assert summary == TraceSummary(
        classes=3,
        scanned_total=10,
        hits_total=3,
        where=["app.py", "gunicorn.conf.py", "."],
    )


def test_summarize_where_dedupes_keeping_first_order():
    trace = [
        SearchProbe(probe="a", target="x", scanned=1, hits=1, where=["a.py", "b.py"]),
        SearchProbe(probe="b", target="y", scanned=1, hits=0, where=["b.py", "c.py"]),
    ]
    assert summarize(trace).where == ["a.py", "b.py", "c.py"]


def test_summarize_empty():
    summary = summarize([])
    assert summary == TraceSummary(classes=0, scanned_total=0, hits_total=0, where=[])


def test_headline():
    trace = [
        SearchProbe(probe="threaded", target="app.run", scanned=4, hits=1, where=["app.py"]),
        SearchProbe(probe="workers", target="gunicorn", scanned=7, hits=2, where=["gunicorn.conf.py"]),
    ]
    assert headline(trace) == "查过 2 类 11 处"


def test_headline_empty():
    assert headline([]) == "查过 0 类 0 处"


def test_summarize_is_frozen():
    summary = summarize([])
    with pytest.raises(AttributeError):
        summary.classes = 9

def test_distinct_scanned_dedups_shared_probe():
    shared = SearchProbe(
        probe="相关实现", target="按模块划分的实现文件", scanned=968, hits=3, where=[]
    )
    trace = [shared, shared, shared]

    assert summarize(trace).scanned_total == 2904
    assert distinct_scanned(trace) == 968


def test_distinct_scanned_keeps_max_for_same_key():
    trace = [
        SearchProbe(probe="压测脚本", target="t", scanned=4, hits=0, where=[]),
        SearchProbe(probe="压测脚本", target="t", scanned=7, hits=2, where=[]),
        SearchProbe(probe="压测脚本", target="t", scanned=5, hits=0, where=[]),
    ]

    assert distinct_scanned(trace) == 7


def test_distinct_scanned_empty_and_distinct_keys():
    assert distinct_scanned([]) == 0
    trace = [
        SearchProbe(probe="a", target="x", scanned=3, hits=0, where=[]),
        SearchProbe(probe="a", target="y", scanned=5, hits=0, where=[]),
    ]

    assert distinct_scanned(trace) == 8