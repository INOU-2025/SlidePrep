"""Tests for OME-TIFF physical-size injection in the stitching step."""

import re
import xml.etree.ElementTree as ET

import numpy as np
import pytest
import tifffile

from src.utils.stitching_utils import inject_physical_size

PIXEL_SIZE = 0.630


def test_inject_physical_size(tmp_path):
    out = tmp_path / "slide.ome.tif"
    tifffile.imwrite(
        str(out),
        np.zeros((64, 64, 3), dtype=np.uint8),
        photometric="rgb",
        metadata={"axes": "YXS"},
    )

    inject_physical_size(str(out), PIXEL_SIZE)

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


def test_inject_physical_size_missing_file_raises():
    """Reading a nonexistent file used to be swallowed by a bare
    `except Exception: return` — it must now raise instead of failing
    silently."""
    with pytest.raises(FileNotFoundError):
        inject_physical_size("/nonexistent/path/to/slide.ome.tif", PIXEL_SIZE)


def test_inject_physical_size_no_pixels_element_raises(tmp_path):
    """A non-empty ImageDescription that isn't OME-XML with a <Pixels>
    element used to silently no-op (zero regex/iter matches, then the
    unmodified XML got written back and the function returned normally).
    It must now raise, and must not have touched the file at all."""
    out = tmp_path / "slide.tif"
    original_description = "<Foo>not OME-XML with a Pixels element</Foo>"
    tifffile.imwrite(
        str(out),
        np.zeros((64, 64, 3), dtype=np.uint8),
        photometric="rgb",
        description=original_description,
    )

    with pytest.raises(RuntimeError):
        inject_physical_size(str(out), PIXEL_SIZE)

    # Confirm nothing was silently patched — the description is unchanged.
    assert tifffile.tiffcomment(str(out)) == original_description
