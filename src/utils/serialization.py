from __future__ import annotations

"""Utility functions for serializing NumPy arrays."""

import base64
import io
from typing import Any

import numpy as np


def array_to_bytes(array: np.ndarray) -> bytes:
    """Serialize a NumPy array into bytes using :func:`numpy.save`.

    Parameters
    ----------
    array:
        Array to serialize.

    Returns
    -------
    bytes
        Byte representation of ``array`` preserving dtype and shape.
    """
    buffer = io.BytesIO()
    np.save(buffer, array, allow_pickle=False)
    return buffer.getvalue()


def bytes_to_array(data: bytes) -> np.ndarray:
    """Deserialize bytes produced by :func:`array_to_bytes` back to an array."""
    buffer = io.BytesIO(data)
    buffer.seek(0)
    return np.load(buffer, allow_pickle=False)


def array_to_base64(array: np.ndarray) -> str:
    """Encode a NumPy array into a base64 string."""
    return base64.b64encode(array_to_bytes(array)).decode("utf-8")


def base64_to_array(data: str) -> np.ndarray:
    """Decode a base64 string back into a NumPy array."""
    return bytes_to_array(base64.b64decode(data))