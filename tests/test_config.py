"""Tests for AppConfigManager loading and config schema validation."""

import pytest
from pydantic import ValidationError

from src.config import BinarizationConfig, ImgConversionConfig
from src.core.app_config_manager import AppConfigManager


def test_minimal_config_loads(minimal_config):
    manager = AppConfigManager(minimal_config)
    assert manager.general_config.output_path == "output"
    assert manager.binarization_config.threshold_method == "combined_differential"
    assert manager.img_conversion_config.format == "png"


def test_binarization_config_rejects_unknown_method():
    with pytest.raises(ValidationError):
        BinarizationConfig(threshold_method="nonexistent")


def test_img_conversion_config_rejects_unknown_format():
    with pytest.raises(ValidationError):
        ImgConversionConfig(format="bmp")
