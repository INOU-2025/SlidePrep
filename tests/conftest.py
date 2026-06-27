"""Shared pytest fixtures for the SlidePrep test suite."""

import json

import numpy as np
import pytest


@pytest.fixture
def gray_image():
    """64×64 uint8 grayscale with a checkerboard stripe pattern."""
    img = np.zeros((64, 64), dtype=np.uint8)
    img[::8, :] = 255
    img[:, ::8] = 255
    return img


@pytest.fixture
def rgb_image(gray_image):
    """64×64 uint8 RGB image derived from the grayscale fixture."""
    return np.stack([gray_image] * 3, axis=-1)


@pytest.fixture
def binary_mask():
    """64×64 uint8 mask with a filled centre square."""
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[20:40, 20:40] = 255
    return mask


@pytest.fixture
def minimal_config(tmp_path):
    """Path to a minimal JSON config that satisfies AppConfigManager without any real files."""
    cfg = {
        "general": {},
        "img_conversion": {"format": "png", "mode": "RGB"},
        "binarization": {"threshold_method": "combined_differential"},
        "log": {"log_to_console": False},
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(cfg))
    return str(p)
