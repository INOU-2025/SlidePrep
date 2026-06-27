"""Tests for BinarizationStep: grayscale and RGB inputs produce binary output."""

from src.config import BinarizationConfig
from src.steps.binarization import BinarizationStep


def test_binarization_grayscale(gray_image):
    step = BinarizationStep(config=BinarizationConfig())
    result = step.run(gray_image)
    assert result.image is not None
    assert result.image.shape == gray_image.shape
    assert set(result.image.flatten().tolist()).issubset({0, 255})


def test_binarization_rgb(rgb_image):
    step = BinarizationStep(config=BinarizationConfig())
    result = step.run(rgb_image)
    assert result.image is not None
    assert set(result.image.flatten().tolist()).issubset({0, 255})
