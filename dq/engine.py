"""A small, dependency-light data-quality rule engine.

Define expectations against a pandas DataFrame with a fluent, chainable API, run
them, and get a structured pass/fail report with offending-row counts. This is
the reusable data-quality gate I put in front of BI models and warehouse loads:
fail fast, fail loud, and say exactly which rows broke which rule.

Expectations
------------
``not_null`` · ``unique`` · ``in_range`` · ``allowed_values`` ·
``matches_regex`` · ``referential`` · ``custom``
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable
import json
import re

import pandas as pd


@dataclass
class Result:
    name: str
    passed: bool
    failed_rows: int
    checked_rows: int
    detail: str = ""

    @property
    def fail_rate(self) -> float:
        return 0.0 if self.checked_rows == 0 else self.failed_rows / self.checked_rows

    def as_dict(self) -> dict:
        return {
            "rule": self.name,
            "passed": self.passed,
            "failed_rows": self.failed_rows,
            "checked_rows": self.checked_rows,
            "fail_rate_pct": round(100 * self.fail_rate, 2),
            "detail": self.detail,
        }


@dataclass
class Suite:
    df: pd.DataFrame
    results: list = field(default_factory=list)

    def _add(self, name: str, mask_failed: pd.Series, detail: str = "") -> "Suite":
        mask_failed = mask_failed.fillna(True) if mask_failed.dtype == bool else mask_failed
        n = int(mask_failed.sum())
        self.results.append(Result(name, n == 0, n, len(self.df), detail))
        return self

    # ---- Expectations ------------------------------------------------------
    def not_null(self, column: str) -> "Suite":
        """No missing values in ``column``."""
        return self._add(f"not_null[{column}]", self.df[column].isna())

    def unique(self, column: str) -> "Suite":
        """Values in ``column`` are unique (each duplicate past the first fails)."""
        return self._add(f"unique[{column}]", self.df[column].duplicated())

    def in_range(self, column: str, low, high) -> "Suite":
        """Numeric values fall within the inclusive ``[low, high]`` range."""
        col = self.df[column]
        return self._add(f"in_range[{column}]({low},{high})",
                         ~col.between(low, high), f"expected {low}..{high}")

    def allowed_values(self, column: str, allowed: Iterable) -> "Suite":
        """Values are drawn only from the ``allowed`` set (categorical guard)."""
        return self._add(f"allowed_values[{column}]",
                         ~self.df[column].isin(set(allowed)),
                         f"allowed={sorted(allowed)}")

    def matches_regex(self, column: str, pattern: str) -> "Suite":
        """String values fully match ``pattern`` (e.g. an email/ID format)."""
        rx = re.compile(pattern)
        bad = ~self.df[column].astype(str).map(lambda v: bool(rx.fullmatch(v)))
        return self._add(f"regex[{column}]", bad, pattern)

    def referential(self, column: str, reference: Iterable,
                    ref_column: str | None = None) -> "Suite":
        """Foreign-key check: every value in ``column`` must exist in ``reference``.

        ``reference`` may be any iterable of valid keys, a pandas ``Series``, or a
        DataFrame (in which case pass ``ref_column``). Nulls are treated as
        orphans — an unresolved key is a broken join waiting to happen.
        """
        if isinstance(reference, pd.DataFrame):
            if ref_column is None:
                raise ValueError("ref_column is required when reference is a DataFrame")
            keys = set(reference[ref_column].dropna())
            label = f"{ref_column}"
        elif isinstance(reference, pd.Series):
            keys = set(reference.dropna())
            label = reference.name or "reference"
        else:
            keys = set(reference)
            label = "reference"
        bad = ~self.df[column].isin(keys)
        return self._add(f"referential[{column}->{label}]", bad,
                         f"{len(keys)} valid keys")

    def custom(self, name: str, fn: Callable[[pd.DataFrame], pd.Series]) -> "Suite":
        """Arbitrary row-level predicate; ``fn`` returns a boolean Series (True = ok)."""
        return self._add(name, ~fn(self.df))

    # ---- Reporting ---------------------------------------------------------
    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    def summary(self) -> dict:
        """Roll-up: rule counts, total offending rows, and an overall pass rate."""
        n = len(self.results)
        passed = sum(r.passed for r in self.results)
        return {
            "rules": n,
            "passed": passed,
            "failed": n - passed,
            "total_failed_rows": sum(r.failed_rows for r in self.results),
            "rows_checked": len(self.df),
            "pass_rate_pct": round(100 * passed / n, 1) if n else 100.0,
            "overall": "PASS" if self.passed else "FAIL",
        }

    def to_records(self) -> list[dict]:
        return [r.as_dict() for r in self.results]

    def to_json(self, **kwargs) -> str:
        return json.dumps(
            {"summary": self.summary(), "results": self.to_records()},
            indent=2, **kwargs,
        )

    def report(self) -> str:
        lines = ["Data-Quality Report", "=" * 56]
        for r in self.results:
            status = "PASS" if r.passed else f"FAIL ({r.failed_rows} rows)"
            extra = f"  -- {r.detail}" if r.detail and not r.passed else ""
            lines.append(f"  [{status:>16}] {r.name}{extra}")
        s = self.summary()
        lines.append("=" * 56)
        lines.append(
            f"OVERALL: {s['overall']}  "
            f"({s['passed']}/{s['rules']} rules, "
            f"{s['total_failed_rows']} offending rows across {s['rows_checked']} checked)"
        )
        return "\n".join(lines)
