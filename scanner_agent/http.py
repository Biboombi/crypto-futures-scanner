from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any


class HttpError(RuntimeError):
    pass


def get_json(url: str, params: dict[str, Any] | None = None, timeout: float = 12.0) -> Any:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "scanner-agent/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001 - convert stdlib network errors into one app error.
        raise HttpError(f"GET {url} failed: {exc}") from exc
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HttpError(f"GET {url} returned invalid JSON") from exc


def post_json(url: str, payload: dict[str, Any], timeout: float = 12.0) -> Any:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "scanner-agent/0.1"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        raise HttpError(f"POST {url} failed: {exc}") from exc
    if not body:
        return {}
    return json.loads(body)
