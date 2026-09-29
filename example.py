"""End-to-end demo of the data-quality framework on a two-table order feed.

Simulates a realistic ingestion check: an ``orders`` table validated for
completeness, uniqueness, ranges, categoricals, format, and — the one that
catches broken joins — referential integrity against a ``customers`` dimension.
Prints the report, writes a JSON + text snapshot, and renders a pass/fail
summary chart in the project house style.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from dq import Suite

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"

# ---- House style -----------------------------------------------------------
INK = "#0f172a"
GRID = "#e2e8f0"
PASS = "#00C2A8"
FAIL = "#F2647C"
ACCENT = "#1E90FF"

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": GRID,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "font.size": 10,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlecolor": INK,
    "text.color": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
})


def build_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """A clean customers dimension and a deliberately dirty orders fact table."""
    rng = np.random.default_rng(7)
    customers = pd.DataFrame({"customer_id": range(1, 201)})

    n = 500
    orders = pd.DataFrame({
        "order_id": range(1, n + 1),                            # clean: unique
        "customer_id": rng.integers(1, 230, n),                 # dirty: some > 200 (orphans)
        "email": rng.choice(
            ["buyer@shop.com", "ops@corp.io", "n/a", "missing"], n,
            p=[0.6, 0.3, 0.06, 0.04]),                          # dirty: bad formats
        "amount": rng.normal(120, 60, n).round(2),              # dirty: some negative
        "status": rng.choice(
            ["paid", "refunded", "pending"], n,
            p=[0.7, 0.15, 0.15]),                               # clean: allowed set
    })
    orders.loc[rng.choice(n, 8, replace=False), "amount"] = np.nan   # dirty: nulls
    return customers, orders


def validate(customers: pd.DataFrame, orders: pd.DataFrame) -> Suite:
    return (Suite(orders)
            .not_null("amount")
            .unique("order_id")
            .in_range("amount", 0, 1000)
            .allowed_values("status", {"paid", "refunded", "pending"})
            .matches_regex("email", r"[^@\s]+@[^@\s]+\.[^@\s]+")
            .referential("customer_id", customers, "customer_id"))


def chart(suite: Suite) -> None:
    """House-style pass/fail summary: offending rows per rule, coloured by status."""
    OUT.mkdir(exist_ok=True)
    recs = suite.to_records()
    names = [r["rule"] for r in recs][::-1]
    rows = [r["failed_rows"] for r in recs][::-1]
    colors = [PASS if r["passed"] else FAIL for r in recs][::-1]
    s = suite.summary()

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(names, rows, color=colors)
    ax.bar_label(bars, padding=4, fontsize=9,
                 labels=[f"{v}" if v else "OK" for v in rows])
    ax.set_title("Data-Quality Gate — Offending Rows per Rule")
    ax.set_xlabel(f"Failed rows (of {s['rows_checked']} checked)")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.margins(x=0.12)

    verdict = "PASS" if suite.passed else "FAIL"
    fig.text(0.99, 0.02,
             f"{verdict}  ·  {s['passed']}/{s['rules']} rules  ·  "
             f"{s['total_failed_rows']} offending rows",
             ha="right", va="bottom", fontsize=10, color=INK, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "dq_report.png", dpi=130)
    plt.close(fig)


def main() -> None:
    customers, orders = build_data()
    suite = validate(customers, orders)
    print(suite.report())

    OUT.mkdir(exist_ok=True)
    (OUT / "report.json").write_text(suite.to_json())
    (OUT / "report.txt").write_text(suite.report())
    chart(suite)
    print(f"\nReport + chart written to {OUT}/")
    raise SystemExit(0 if suite.passed else 1)


if __name__ == "__main__":
    main()
