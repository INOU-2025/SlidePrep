"""MutableMapping wrapper around detection results with JSON round-trip support for numpy arrays and enums."""

import json
from enum import Enum
from collections.abc import MutableMapping, Mapping
from typing import Any, Dict, Mapping as TMapping
import numpy as np
from .models import Orientation, DetectionRegion, DetectionStrategy

# Registry built from real class names to prevent member typos
_ENUM_CLASSES = (Orientation, DetectionRegion, DetectionStrategy)
ENUM_REGISTRY: TMapping[str, type[Enum]] = {
    cls.__name__: cls for cls in _ENUM_CLASSES}


def _enum_to_str(e: Enum) -> str:
    return f"{e.__class__.__name__}.{e.name}"


def _str_to_enum(s: str) -> Enum:
    cls_name, member_name = s.split(".", 1)
    return ENUM_REGISTRY[cls_name][member_name]



def _encode(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return _enum_to_str(obj)
    if isinstance(obj, np.ndarray):
        return {"__ndarray__": obj.tolist(), "dtype": str(obj.dtype), "shape": obj.shape}
    if isinstance(obj, (np.integer, np.floating, np.bool_)):
        return obj.item()
    if isinstance(obj, dict):
        return {(_enum_to_str(k) if isinstance(k, Enum) else k): _encode(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_encode(x) for x in obj]
    if isinstance(obj, tuple):
        return {"__tuple__": [_encode(x) for x in obj]}
    if isinstance(obj, set):
        return [_encode(x) for x in obj]
    return obj


def _decode(obj: Any) -> Any:
    if isinstance(obj, str) and "." in obj:
        cls_name, member = obj.split(".", 1)
        if cls_name in ENUM_REGISTRY and member in ENUM_REGISTRY[cls_name].__members__:
            return _str_to_enum(obj)
    if isinstance(obj, dict):
        if "__ndarray__" in obj and "dtype" in obj and "shape" in obj:
            arr = np.array(obj["__ndarray__"], dtype=np.dtype(obj["dtype"]))
            if tuple(arr.shape) != tuple(obj["shape"]):
                arr = arr.reshape(tuple(obj["shape"]))
            return arr
        if "__tuple__" in obj:
            return tuple(_decode(x) for x in obj["__tuple__"])
        return {(_decode(k) if isinstance(k, str) else k): _decode(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decode(x) for x in obj]
    return obj


def _plainify(obj: Any):
    if isinstance(obj, (Enum, np.ndarray)):
        return obj
    if isinstance(obj, Mapping):
        return {_plainify(k): _plainify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return type(obj)(_plainify(x) for x in obj)
    return obj



class DetectionResultDict(MutableMapping):
    """MutableMapping wrapping a detection results dict with JSON round-trip support.

    Transparently serialises numpy arrays, enums, and tuples via a tagged-object
    scheme so the full results can be written to and restored from JSON without
    losing type information.
    """
    def __init__(self, *args, **kwargs):
        self._data: Dict[Any, Any] = dict(*args, **kwargs)

    def __getitem__(self, key): return self._data[key]
    def __setitem__(self, key, value): self._data[key] = value
    def __delitem__(self, key): del self._data[key]
    def __iter__(self): return iter(self._data)
    def __len__(self): return len(self._data)

    def to_json(self, path: str, *, indent: int | None = 2) -> None:
        payload = _encode(self._data)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=indent)

    @classmethod
    def write_batch(cls, path: str, batch: list, *, indent: int | None = 2) -> None:
        """Write a list of per-item results (e.g. ``{"filename": ..., "result": ...}``).

        Unlike ``to_json``, this does not route the list through ``dict(*args)`` —
        passing a list of same-shaped dicts there silently collapses them into a
        single pair via dict()'s iterable-of-pairs semantics, discarding the data.
        """
        payload = _encode(batch)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, path: str) -> "DetectionResultDict":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(_decode(data))

    def to_plain_dict(self) -> dict:
        return _plainify(self._data)
