"""Per-rule tests for the data-quality engine, each on crafted data with a
known number of violations. Run with: python -m pytest -q
"""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dq import Suite


# ---- not_null --------------------------------------------------------------
def test_not_null_counts_missing():
    df = pd.DataFrame({"v": [1, None, 3, None]})
    s = Suite(df).not_null("v")
    assert not s.passed
    assert s.results[0].failed_rows == 2


def test_not_null_passes_when_complete():
    s = Suite(pd.DataFrame({"v": [1, 2, 3]})).not_null("v")
    assert s.passed and s.results[0].failed_rows == 0


# ---- unique ----------------------------------------------------------------
def test_unique_flags_duplicates_beyond_first():
    df = pd.DataFrame({"id": [1, 1, 1, 2]})   # two extra 1s
    s = Suite(df).unique("id")
    assert not s.passed
    assert s.results[0].failed_rows == 2


def test_unique_passes_when_distinct():
    s = Suite(pd.DataFrame({"id": [1, 2, 3]})).unique("id")
    assert s.passed


# ---- in_range --------------------------------------------------------------
def test_in_range_bounds_inclusive():
    df = pd.DataFrame({"age": [17, 18, 90, 91, 45]})   # 17 and 91 out
    s = Suite(df).in_range("age", 18, 90)
    assert s.results[0].failed_rows == 2


def test_in_range_null_counts_as_failure():
    df = pd.DataFrame({"age": [20, None, 30]})
    s = Suite(df).in_range("age", 0, 100)
    assert s.results[0].failed_rows == 1


# ---- allowed_values --------------------------------------------------------
def test_allowed_values_flags_out_of_set():
    df = pd.DataFrame({"status": ["a", "b", "c", "a"]})
    s = Suite(df).allowed_values("status", {"a", "b"})
    assert s.results[0].failed_rows == 1   # the single "c"


# ---- matches_regex ---------------------------------------------------------
def test_regex_full_match_only():
    df = pd.DataFrame({"email": ["a@b.com", "bad", "x@y.io", "a@b.com extra"]})
    s = Suite(df).matches_regex("email", r"[^@\s]+@[^@\s]+\.[^@\s]+")
    assert s.results[0].failed_rows == 2   # "bad" and the trailing-text one


# ---- referential -----------------------------------------------------------
def test_referential_against_dataframe():
    dim = pd.DataFrame({"customer_id": [1, 2, 3]})
    fact = pd.DataFrame({"customer_id": [1, 2, 4, 5, 3]})   # 4 and 5 orphaned
    s = Suite(fact).referential("customer_id", dim, "customer_id")
    assert not s.passed
    assert s.results[0].failed_rows == 2


def test_referential_against_iterable_and_null_is_orphan():
    fact = pd.DataFrame({"fk": [1, 2, None, 9]})   # None + 9 orphaned
    s = Suite(fact).referential("fk", {1, 2, 3})
    assert s.results[0].failed_rows == 2


def test_referential_requires_ref_column_for_dataframe():
    dim = pd.DataFrame({"id": [1, 2]})
    with pytest.raises(ValueError):
        Suite(pd.DataFrame({"fk": [1]})).referential("fk", dim)


# ---- custom ----------------------------------------------------------------
def test_custom_predicate():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [2, 2, 1]})   # a<=b fails on row 3
    s = Suite(df).custom("a_le_b", lambda d: d["a"] <= d["b"])
    assert s.results[0].failed_rows == 1


# ---- chaining, summary, reporting -----------------------------------------
def test_chaining_and_overall_pass():
    df = pd.DataFrame({"id": [1, 2, 3], "v": [10, 20, 30]})
    s = (Suite(df).not_null("v").unique("id").in_range("v", 0, 100))
    assert s.passed
    assert s.summary()["pass_rate_pct"] == 100.0


def test_summary_rollup():
    df = pd.DataFrame({"id": [1, 1], "v": [10, 999]})
    s = Suite(df).unique("id").in_range("v", 0, 100)
    summ = s.summary()
    assert summ["rules"] == 2
    assert summ["failed"] == 2
    assert summ["total_failed_rows"] == 2
    assert summ["overall"] == "FAIL"


def test_report_and_json_serialisable():
    import json
    df = pd.DataFrame({"id": [1, 2], "v": [5, 5]})
    s = Suite(df).unique("id").not_null("v")
    assert "Data-Quality Report" in s.report()
    parsed = json.loads(s.to_json())
    assert parsed["summary"]["rules"] == 2
    assert len(parsed["results"]) == 2
