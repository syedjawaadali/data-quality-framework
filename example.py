"""Demonstrate the data-quality framework on a sample dataset."""
import numpy as np
import pandas as pd
from dq import Suite

rng = np.random.default_rng(3)
df = pd.DataFrame({
    "id": list(range(1, 100)) + [99],          # duplicate id
    "email": ["a@b.com"] * 99 + ["not-an-email"],
    "age": rng.integers(10, 95, 100),
    "status": rng.choice(["active", "closed", "BAD"], 100),
})
df.loc[5, "age"] = None                          # a null

suite = (Suite(df)
         .not_null("age")
         .unique("id")
         .in_range("age", 18, 90)
         .allowed_values("status", {"active", "closed"})
         .matches_regex("email", r"[^@]+@[^@]+\.[^@]+"))

print(suite.report())
raise SystemExit(0 if suite.passed else 1)
