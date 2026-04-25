"""Postgres CSV patcher."""

from .common import (
    Error,
    ResClass,
)
from .csv_patcher import patch_csv_timestamp


__all__ = (
    Error,
    ResClass,
    patch_csv_timestamp,
)
__author__ = "0xMihalich"
__version__ = "0.1.1"
