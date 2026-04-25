from ctypes import (
    Structure,
    CDLL,
    c_char_p,
)
from json import loads
from pathlib import Path
from sys import platform


class PgQueryParseResult(Structure):
    _fields_ = [
        ("parse_tree", c_char_p),
        ("error_message", c_char_p),
    ]


class PgQuery:
    def __init__(self):
        if platform == "win32":
            lib_name = "libpg_query.dll"
        elif platform == "darwin":
            lib_name = "libpg_query.dylib"
        else:
            lib_name = "libpg_query.so"

        self._lib = CDLL(str(Path(__file__).parent / lib_name))
        self._setup_functions()

    def _setup_functions(self):
        self._lib.pg_query_parse.argtypes = [c_char_p]
        self._lib.pg_query_parse.restype = PgQueryParseResult
        self._lib.pg_query_free_parse_result.argtypes = [PgQueryParseResult]
        self._lib.pg_query_free_parse_result.restype = None

    def parse(self, query: str) -> PgQueryParseResult:
        return self._lib.pg_query_parse(query.encode("utf-8"))

    def free(self, result: PgQueryParseResult) -> None:
        self._lib.pg_query_free_parse_result(result)

    def query_stmts(self, query: str) -> list[dict[str, str | int]]:
        return loads(self.parse(query).parse_tree)["stmts"]
