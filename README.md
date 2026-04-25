# Postgres CSV Patcher

A tool for patching `timestamp`/`timestamptz` columns to `::timestamp(0)` precision in CSV dump queries. Uses native `libpg_query` PostgreSQL parser via `ctypes` for precise AST analysis.

## Why?

When dumping data to CSV for systems like ClickHouse, `timestamp` values with microseconds (`2026-04-22 09:28:49.805664`) are not accepted. This library automatically wraps all `timestamp`/`timestamptz` columns with `::timestamp(0)` to truncate microseconds.

## Features

- **Native PostgreSQL parser** — uses `libpg_query` directly, no Python wrappers
- **Cross-platform** — Windows (x86/x64), macOS (x86_64/arm64), Linux
- **Precise column detection** — handles column aliases, table prefixes, quoted identifiers
- **Complex expressions** — functions (`now()`, `date_trunc(...)`), expressions (`created_at + interval`), `CURRENT_TIMESTAMP`
- **Wildcard expansion** — `SELECT *`, `table.*`
- **Multiquery support** — processes the last `SELECT` in multi-statement queries
- **Zero dependencies** — only Python stdlib and `libpg_query` (auto-built on install)

## Installation

```bash
pip install postgres-csvpatcher
```

The package automatically clones and builds `libpg_query` during installation.

### Requirements

- **Windows:** Visual Studio 2022 with C++ tools
- **macOS:** Xcode Command Line Tools (`xcode-select --install`)
- **Linux:** `gcc`, `make`

## Usage

```python
from . import patch_csv_timestamp

# Columns dict: {column_name: data_type}
columns = {
    "id": "int4",
    "name": "varchar",
    "created_at": "timestamp",
    "updated_at": "timestamptz",
}

# Simple query
query = "SELECT id, created_at FROM users"
patched, table = patch_csv_timestamp(query, "users", columns)
print(patched)
# SELECT id, created_at::timestamp(0) FROM users

# Query with functions
query = "SELECT now() as _date_load FROM orders"
patched, table = patch_csv_timestamp(query, "orders", columns)
print(patched)
# SELECT now()::timestamp(0) as _date_load FROM orders

# Query with wildcard
query = "SELECT * FROM users"
patched, table = patch_csv_timestamp(query, "users", columns)
print(patched)
# SELECT "id", "name", "created_at"::timestamp(0) AS "created_at", "updated_at"::timestamp(0) AS "updated_at" FROM users

# Build query from table name only (no query provided)
patched, table = patch_csv_timestamp(None, "users", columns)
print(patched)
# SELECT
#     "id"
#   , "name"
#   , "created_at"::timestamp(0)
#   , "updated_at"::timestamp(0)
# FROM
#     users
```

## API

```python
def patch_csv_timestamp(
    query: str | None,
    table: str | None,
    columns: dict[str, str],
) -> tuple[str, str | None]:
```

### Parameters

- `query` — SQL query string, or `None` to auto-generate query from table name
- `table` — table name (used when `query` is `None`)
- `columns` — dict mapping column names to PostgreSQL data types (`{"column_name": "data_type"}`)

### Returns

`(patched_query, table)` — tuple with modified query and table name.

## How It Works

1. Parses SQL via native `libpg_query` → JSON AST
2. Finds the last `SELECT` statement (final output for multiquery)
3. Detects `timestamp`/`timestamptz` columns from metadata
4. For each timestamp column:
   - **ColumnRef** (simple column): adds `::timestamp(0)` inline
   - **FuncCall** (`now()`, `date_trunc(...)`): wraps with `::timestamp(0)`
   - **A_Expr** (expressions): wraps in parentheses + `::timestamp(0)`
   - **SQLValueFunction** (`CURRENT_TIMESTAMP`): wraps with `::timestamp(0)`
   - **TypeCast** (already casted): skips or replaces
5. Expands `SELECT *` and `table.*` wildcards
6. Preserves original formatting, aliases, and query structure

## Supported Column Types

| Type | Example Input | Output |
|------|--------------|--------|
| `ColumnRef` | `created_at` | `created_at::timestamp(0)` |
| `ColumnRef` (alias) | `created_at as ct` | `created_at::timestamp(0) as ct` |
| `ColumnRef` (quoted) | `"created_at"` | `"created_at"::timestamp(0)` |
| `ColumnRef` (table prefix) | `e.event_time` | `e.event_time::timestamp(0)` |
| `FuncCall` | `now()` | `now()::timestamp(0)` |
| `FuncCall` (arguments) | `date_trunc('month', created_at)` | `date_trunc('month', created_at)::timestamp(0)` |
| `A_Expr` | `created_at + interval '1 day'` | `(created_at + interval '1 day')::timestamp(0)` |
| `SQLValueFunction` | `CURRENT_TIMESTAMP` | `CURRENT_TIMESTAMP::timestamp(0)` |
| `TypeCast` | `'2025-01-01'::timestamptz` | `'2025-01-01'::timestamp(0)` |
| `Wildcard` | `SELECT *` | `SELECT "col1", "col2"::timestamp(0), ...` |

## Module Structure

### ResClass — Column Class Enum

```python
from enum import Enum

class ResClass(str, Enum):
    CAST = "TypeCast"       # TypeCast (e.g., '2025-01-01'::timestamptz)
    CONST = "A_Const"       # Constant (e.g., 'константа')
    COLUMN = "ColumnRef"    # Column reference (e.g., created_at)
    EXPR = "A_Expr"         # Expression with operators (e.g., created_at + interval)
    FUNC = "FuncCall"       # Function call (e.g., now())
    SQLVALUE = "SQLValueFunction"  # SQL value function (e.g., CURRENT_TIMESTAMP)
```

Enum mapping AST node types to readable names. Used by `__column_class()` to determine how to handle each `ResTarget` in the `SELECT` clause.

| Value | AST Node | Example |
|-------|----------|---------|
| `CAST` | `TypeCast` | `'2025-01-01'::timestamptz` |
| `CONST` | `A_Const` | `'константа'` |
| `COLUMN` | `ColumnRef` | `created_at` |
| `EXPR` | `A_Expr` | `now() - interval '1 day'` |
| `FUNC` | `FuncCall` | `now()`, `date_trunc(...)` |
| `SQLVALUE` | `SQLValueFunction` | `CURRENT_TIMESTAMP` |

### Error — Exception Classes

```python
class CSVPatcherError(Exception):
    """Base CSVPatcher error."""

class CSVPatcherValueError(CSVPatcherError, ValueError):
    """CSVPatcher value error."""

class CSVPatcherTypeError(CSVPatcherError, TypeError):
    """CSVPatcher type error."""
```

| Exception | Base Classes | Raised When |
|-----------|-------------|-------------|
| `Error.CSVPatcherError` | `Exception` | Base class for all patcher errors |
| `Error.CSVPatcherValueError` | `CSVPatcherError`, `ValueError` | Invalid input values (empty query + table, mismatched columns) |
| `Error.CSVPatcherTypeError` | `CSVPatcherError`, `TypeError` | Wrong type for `columns` parameter |

### PgQuery — Native Parser Wrapper

```python
from ctypes import Structure, CDLL, c_char_p

class PgQueryParseResult(Structure):
    _fields_ = [
        ("parse_tree", c_char_p),    # JSON string with AST
        ("error_message", c_char_p), # Error message (NULL on success)
    ]

class PgQuery:
    def __init__(self):
        # Loads native library: libpg_query.dll/.dylib/.so
        ...

    def parse(self, query: str) -> PgQueryParseResult:
        # Parses SQL to JSON AST via libpg_query
        ...

    def free(self, result: PgQueryParseResult) -> None:
        # Frees memory allocated by libpg_query
        ...

    def query_stmts(self, query: str) -> list[dict[str, str | int]]:
        # Parses SQL and returns list of statements (stmts)
        ...
```

`PgQueryParseResult` mirrors the C struct from `libpg_query`:

| Field | C Type | Python Type | Description |
|-------|--------|-------------|-------------|
| `parse_tree` | `char*` | `bytes` | JSON string with parsed AST |
| `error_message` | `char*` | `bytes` | Error message or `NULL` |

`PgQuery` handles cross-platform library loading:

| Platform | Library Name |
|----------|-------------|
| Windows | `libpg_query.dll` |
| macOS | `libpg_query.dylib` |
| Linux | `libpg_query.so` |

## License

MIT
