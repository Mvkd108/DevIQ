from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import ModuleType

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def ensure_fastapi_stub() -> None:
    if "fastapi" in sys.modules:
        return

    fastapi = ModuleType("fastapi")

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class FastAPI:
        def __init__(self, *args, **kwargs):
            pass

        def add_middleware(self, *args, **kwargs):
            return None

        def get(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

        def post(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

    fastapi.FastAPI = FastAPI
    fastapi.HTTPException = HTTPException
    fastapi.Header = lambda default=None, alias=None: default
    sys.modules["fastapi"] = fastapi

    if "fastapi.middleware" not in sys.modules:
        sys.modules["fastapi.middleware"] = ModuleType("fastapi.middleware")

    if "fastapi.middleware.cors" not in sys.modules:
        cors = ModuleType("fastapi.middleware.cors")

        class CORSMiddleware:
            pass

        cors.CORSMiddleware = CORSMiddleware
        sys.modules["fastapi.middleware.cors"] = cors


ensure_fastapi_stub()

from fastapi import HTTPException  # noqa: E402
from storage import request_json  # noqa: E402


class StorageTests(unittest.TestCase):
    def test_request_json_rejects_missing_supabase_base_url_with_clear_http_error(self) -> None:
        with self.assertRaises(HTTPException) as context:
            request_json("GET", "/rest/v1/req_code_mapping?select=issue_id", {})

        self.assertEqual(context.exception.status_code, 503)
        self.assertIn("SUPABASE_URL", context.exception.detail)


if __name__ == "__main__":
    unittest.main()
