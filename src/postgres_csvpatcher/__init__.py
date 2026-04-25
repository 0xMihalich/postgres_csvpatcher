"""Postgres CSV patcher."""

from .common import (
    Error,
    ResClass,
)
from .core import (
    PgQuery,
    PgQueryParseResult,
)
from .csv_patcher import patch_csv_timestamp


__all__ = (
    Error,
    PgQuery,
    PgQueryParseResult,
    ResClass,
    patch_csv_timestamp,
)
__author__ = "0xMihalich"
__version__ = "0.1.0"
