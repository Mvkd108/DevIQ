from __future__ import annotations

from typing import Any, Optional

from delivery_timeline_normalization import sort_events_desc, value_present

CONNECTOR_CONTAINER_KEYS = ("connector_payload", "payload", "metadata", "details", "data")


def latest_connector_value(
    events: list[dict[str, Any]],
    *,
    flat_keys: tuple[str, ...] = (),
    nested_paths: tuple[tuple[str, ...], ...] = (),
) -> tuple[Any, Optional[str], Optional[dict[str, Any]]]:
    for event in sort_events_desc(events):
        for key in flat_keys:
            value = event.get(key)
            if value_present(value):
                return value, key, event

        for container, prefix in iter_event_containers(event):
            for path in nested_paths:
                value = get_nested_value(container, path)
                if value_present(value):
                    return value, format_path_label(prefix, path), event

    return None, None, None


def iter_event_containers(event: dict[str, Any]) -> list[tuple[dict[str, Any], Optional[str]]]:
    containers: list[tuple[dict[str, Any], Optional[str]]] = [(event, None)]
    for key in CONNECTOR_CONTAINER_KEYS:
        value = event.get(key)
        if isinstance(value, dict):
            containers.append((value, key))
    return containers


def get_nested_value(container: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = container
    for part in path:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def format_path_label(prefix: Optional[str], path: tuple[str, ...]) -> str:
    joined = ".".join(path)
    return f"{prefix}.{joined}" if prefix else joined
