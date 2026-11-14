"""C-TRACE@1：轨迹统计、去重保序与空输入。"""

import pytest

from gap_engine.schema import SearchProbe
from gap_engine.trace import TraceSummary, headline, summarize


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