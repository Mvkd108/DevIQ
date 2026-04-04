from __future__ import annotations

import json
from typing import Any, Optional
from urllib import error, parse, request

from fastapi import HTTPException


def request_json(
    method: str,
    url: str,
    default_headers: dict[str, str],
    payload: Optional[Any] = None,
    headers: Optional[dict[str, str]] = None,
) -> Any:
    if not str(url or "").startswith(("http://", "https://")):
        raise HTTPException(
            status_code=503,
            detail="Supabase REST endpoint is not configured. Set SUPABASE_URL before using data-backed endpoints.",
        )
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(url, method=method, headers=headers or default_headers, data=data)
    try:
        with request.urlopen(req, timeout=60) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise HTTPException(status_code=exc.code, detail=detail) from exc
    except error.URLError as exc:
        raise HTTPException(status_code=502, detail=str(exc.reason)) from exc


def get_rows(
    base_rest_url: str,
    default_headers: dict[str, str],
    table: str,
    select: str,
    order: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[dict[str, Any]]:
    params = {"select": select}
    if order:
        params["order"] = order
    if limit:
        params["limit"] = str(limit)
    query = parse.urlencode(params, safe="*,()")
    response = request_json("GET", f"{base_rest_url}/{table}?{query}", default_headers)
    if not isinstance(response, list):
        raise HTTPException(status_code=500, detail=f"Unexpected response for {table}")
    return response


def get_rows_filtered(
    base_rest_url: str,
    default_headers: dict[str, str],
    table: str,
    select: str,
    filters: Optional[dict[str, str]] = None,
    order: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[dict[str, Any]]:
    params = {"select": select}
    if filters:
        params.update(filters)
    if order:
        params["order"] = order
    if limit:
        params["limit"] = str(limit)
    query = parse.urlencode(params, safe="*,()")
    response = request_json("GET", f"{base_rest_url}/{table}?{query}", default_headers)
    if not isinstance(response, list):
        raise HTTPException(status_code=500, detail=f"Unexpected response for {table}")
    return response


def patch_row(
    base_rest_url: str,
    default_headers: dict[str, str],
    table: str,
    filters: str,
    payload: dict[str, Any],
) -> Any:
    headers = {
        **default_headers,
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    return request_json("PATCH", f"{base_rest_url}/{table}?{filters}", default_headers, payload=payload, headers=headers)


def post_rows(
    base_rest_url: str,
    default_headers: dict[str, str],
    table: str,
    payload: list[dict[str, Any]],
    upsert: bool = False,
    on_conflict: Optional[str] = None,
) -> Any:
    headers = {
        **default_headers,
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    if upsert:
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"

    query = ""
    if on_conflict:
        query = f"?on_conflict={parse.quote(on_conflict)}"
    return request_json("POST", f"{base_rest_url}/{table}{query}", default_headers, payload=payload, headers=headers)


def delete_rows(
    base_rest_url: str,
    default_headers: dict[str, str],
    table: str,
    filters: str,
) -> Any:
    headers = {
        **default_headers,
        "Prefer": "return=representation",
    }
    return request_json("DELETE", f"{base_rest_url}/{table}?{filters}", default_headers, headers=headers)
