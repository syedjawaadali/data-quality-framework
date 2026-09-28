# Data-Quality Framework

A small, dependency-light **rule engine** for validating pandas DataFrames —
the reusable data-quality gate pattern I bring to governance and
single-source-of-truth initiatives. Chainable expectations, a structured
pass/fail report, and offending-row counts.

## Expectations
`not_null` · `unique` · `in_range` · `allowed_values` · `matches_regex` · `custom`

## Usage
```python
from dq import Suite
suite = (Suite(df)
         .not_null("age")
         .unique("id")
         .in_range("age", 18, 90)
         .allowed_values("status", {"active", "closed"}))
print(suite.report())
assert suite.passed
```

## Run the demo & tests
```bash
pip install -r requirements.txt
python example.py
python tests/test_engine.py
```

## Stack
`pandas` · pure-Python rule engine

---
Part of my data engineering portfolio — [github.com/syedjawaadali](https://github.com/syedjawaadali)
