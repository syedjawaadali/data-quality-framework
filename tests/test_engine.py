"""Minimal tests — run with: python -m pytest  (or python tests/test_engine.py)"""
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dq import Suite


def test_all_pass():
    df = pd.DataFrame({"id": [1, 2, 3], "v": [10, 20, 30]})
    s = Suite(df).not_null("v").unique("id").in_range("v", 0, 100)
    assert s.passed


def test_detects_failures():
    df = pd.DataFrame({"id": [1, 1], "v": [10, 999]})
    s = Suite(df).unique("id").in_range("v", 0, 100)
    assert not s.passed
    assert s.results[0].failed_rows == 1


if __name__ == "__main__":
    test_all_pass(); test_detects_failures()
    print("All tests passed.")
