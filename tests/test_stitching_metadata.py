"""Tests for OME-TIFF physical-size injection in the stitching step."""

import re
import xml.etree.ElementTree as ET

import numpy as np
import pytest
import tifffile

from src.steps.stitching import _inject_physical_size

PIXEL_SIZE = 0.630


def test_inject_physical_size(tmp_path):
    out = tmp_path / "slide.ome.tif"
    tifffile.imwrite(
        str(out),
        np.zeros((64, 64, 3), dtype=np.uint8),
        photometric="rgb",
        metadata={"axes": "YXS"},
    )

    _inject_physical_size(str(out), PIXEL_SIZE)

    with tifffile.TiffFile(str(out)) as tif:
        xml_str = tif.ome_metadata
    assert xml_str, "OME-XML not found after injection"

    ns_match = re.search(r'xmlns="([^"]*)"', xml_str)
    ns = ns_match.group(1) if ns_match else ""
    ns_prefix = f"{{{ns}}}" if ns else ""
    root = ET.fromstring(xml_str)
    pixels = root.find(f".//{ns_prefix}Pixels")
    assert pixels is not None
    assert float(pixels.get("PhysicalSizeX")) == pytest.approx(PIXEL_SIZE)
    assert float(pixels.get("PhysicalSizeY")) == pytest.approx(PIXEL_SIZE)
    assert pixels.get("PhysicalSizeXUnit") == "µm"
    assert pixels.get("PhysicalSizeYUnit") == "µm"
