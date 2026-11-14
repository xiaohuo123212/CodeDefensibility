import pytest

from src.calc import add, divide


def test_add_positive_numbers():
    assert add(1, 2) == 3


def test_divide_returns_float():
    assert divide(3, 2) == 1.5


def test_divide_by_zero_raises():
    with pytest.raises(ZeroDivisionError):
        divide(1, 0)