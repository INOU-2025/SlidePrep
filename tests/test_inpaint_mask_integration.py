"""Integration test: inpaint mask export driven end-to-end over sample_data/."""

import json
import os
import shutil
from glob import glob

import cv2
import numpy as np
import pytest
import tifffile

from src.core.app_config_manager import AppConfigManager
from src.core.pipeline_service import PipelineService
from src.utils import get_extension_for_format

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_data")


@pytest.mark.skipif(not shutil.which("ashlar"), reason="ashlar CLI not installed")
def test_inpaint_mask_over_sample_data(tmp_path):
    with open(os.path.join(SAMPLE_DIR, "config.json")) as f:
        config_data = json.load(f)

    output_dir = str(tmp_path / "output")
    config_data["general"]["input_path"] = os.path.join(SAMPLE_DIR, "tiles")
    config_data["general"]["output_path"] = output_dir
    config_data["log"]["log_to_file"] = False
    config_data["debug"] = {"save_composite_img": False, "save_aggregated_data": False}

    config_manager = AppConfigManager.from_dict(config_data)
    service = PipelineService(config=config_manager)
    os.makedirs(output_dir, exist_ok=True)
    ext = get_extension_for_format(service.config.img_conversion_config.format)

    for tile_path in sorted(glob(os.path.join(SAMPLE_DIR, "tiles", "*.jpg"))):
        gray = cv2.imread(tile_path, cv2.IMREAD_GRAYSCALE)
        result = service.run(gray, image_path=tile_path)
        output_image = result.image
        if output_image.ndim == 3:
            output_image = cv2.cvtColor(output_image, cv2.COLOR_RGB2GRAY)
        name = os.path.splitext(os.path.basename(tile_path))[0]
        out_path = os.path.join(output_dir, f"{name}{ext}")
        cv2.imwrite(out_path, output_image)
        service.write_tile_mask(out_path)

    stitch_result = service.stitch(output_dir)
    ome_path = stitch_result.data
    mask_path = stitch_result.metadata["inpaint_mask_path"]

    assert os.path.exists(ome_path)
    assert mask_path is not None and os.path.exists(mask_path)

    with tifffile.TiffFile(ome_path) as tif:
        ome_yx = tif.series[0].shape[-2:]
    mask_arr = tifffile.imread(mask_path)

    assert mask_arr.shape[-2:] == ome_yx
    assert mask_arr.dtype == np.uint8
    assert set(np.unique(mask_arr)).issubset({0, 255})
    assert mask_arr.sum() > 0  # real reticle cross-hairs -> detection should fire
