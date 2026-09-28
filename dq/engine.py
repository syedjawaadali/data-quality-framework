"""A small, dependency-light data-quality rule engine.

Define expectations against a DataFrame, run them, and get a structured report
with pass/fail status and the count of offending rows. Inspired by the
governance and data-quality gates I build on production BI platforms.
"""
from dataclasses import dataclass, field
from typing import Callable
import re
import pandas as pd


@dataclass
class Result:
    name: str
    passed: bool
    failed_rows: int
    detail: str = ""


@dataclass
class Suite:
    df: pd.DataFrame
    results: list = field(default_factory=list)

    def _add(self, name, mask_failed, detail=""):
        n = int(mask_failed.sum())
        self.results.append(Result(name, n == 0, n, detail))
        return self

    def not_null(self, column):
        return self._add(f"not_null[{column}]", self.df[column].isna())

    def unique(self, column):
        return self._add(f"unique[{column}]", self.df[column].duplicated())

    def in_range(self, column, low, high):
        col = self.df[column]
        return self._add(f"in_range[{column}]({low},{high})",
                         ~col.between(low, high), f"expected {low}..{high}")

    def allowed_values(self, column, allowed):
        return self._add(f"allowed_values[{column}]",
                         ~self.df[column].isin(allowed),
                         f"allowed={sorted(allowed)}")

    def matches_regex(self, column, pattern):
        rx = re.compile(pattern)
        bad = ~self.df[column].astype(str).map(lambda v: bool(rx.fullmatch(v)))
        return self._add(f"regex[{column}]", bad, pattern)

    def custom(self, name, fn: Callable[[pd.DataFrame], pd.Series]):
        return self._add(name, ~fn(self.df))

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    def report(self) -> str:
        lines = ["Data-Quality Report", "=" * 50]
        for r in self.results:
            status = "PASS" if r.passed else f"FAIL ({r.failed_rows} rows)"
            extra = f"  -- {r.detail}" if r.detail and not r.passed else ""
            lines.append(f"  [{status:>16}] {r.name}{extra}")
        lines.append("=" * 50)
        lines.append(f"OVERALL: {'PASS' if self.passed else 'FAIL'}")
        return "\n".join(lines)
