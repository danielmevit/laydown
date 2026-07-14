"""
Presets — the value store, on disk.

Because every setting lives in one dict keyed by schema target, a preset is that
dict and nothing more. Enums and dataclasses are written as tagged objects so the
file stays readable and a hand-edit is possible.

Unknown keys are dropped on load rather than raising: a preset written by a future
version should still load what this one understands.
"""

import json
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any

from pressready.engine import data_model
from pressready.ui.schema import defaults

FORMAT_VERSION = 1


def _encode(value: Any) -> Any:
    if isinstance(value, Enum):
        return {"__enum__": type(value).__name__, "value": value.name}
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "__dataclass__": type(value).__name__,
            "fields": {f.name: _encode(getattr(value, f.name)) for f in fields(value)},
        }
    if isinstance(value, (list, tuple)):
        return [_encode(v) for v in value]
    return value


def _decode(value: Any) -> Any:
    if isinstance(value, list):
        return [_decode(v) for v in value]
    if not isinstance(value, dict):
        return value

    if "__enum__" in value:
        enum_cls = getattr(data_model, value["__enum__"], None)
        if enum_cls is None:
            raise ValueError(f"Unknown setting type: {value['__enum__']}")
        try:
            return enum_cls[value["value"]]
        except KeyError:
            raise ValueError(
                f"{value['__enum__']} has no option {value['value']!r} in this version"
            ) from None

    if "__dataclass__" in value:
        cls = getattr(data_model, value["__dataclass__"], None)
        if cls is None:
            raise ValueError(f"Unknown setting group: {value['__dataclass__']}")
        known = {f.name for f in fields(cls)}
        return cls(**{k: _decode(v) for k, v in value["fields"].items() if k in known})

    return value


def save_preset(path: str, values: dict) -> None:
    payload = {
        "format": FORMAT_VERSION,
        "application": "PressReady",
        "values": {k: _encode(v) for k, v in values.items()},
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def load_preset(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict) or "values" not in payload:
        raise ValueError("That file is not a PressReady preset")
    if payload.get("format", 0) > FORMAT_VERSION:
        raise ValueError(
            f"This preset was written by a newer PressReady (format "
            f"{payload['format']}, this build reads {FORMAT_VERSION})"
        )

    known = set(defaults()) | {"preprocessors", "marks"}
    return {k: _decode(v) for k, v in payload["values"].items() if k in known}
