"""dq — a small, chainable data-quality rule engine for pandas DataFrames."""
from .engine import Result, Suite  # noqa: F401

__all__ = ["Suite", "Result"]
__version__ = "0.2.0"
