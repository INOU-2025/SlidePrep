"""Tests for OME-TIFF physical-size injection in the stitching step."""

import re
import shutil
from pathlib import Path
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
    assert pixels.get("PhysicalSizeXUnit") in (None, "µm")
    assert pixels.get("PhysicalSizeYUnit") in (None, "µm")
    assert "&#" not in xml_str


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


def _write_ashlar_style(path, unit_attrs=True, size=0.63):
    """Two-channel pyramidal OME-TIFF as ashlar writes it (literal µm)."""
    pixels = {}
    if size is not None:
        pixels = {"PhysicalSizeX": size, "PhysicalSizeY": size}
        if unit_attrs:
            pixels.update(PhysicalSizeXUnit="\u00b5m", PhysicalSizeYUnit="\u00b5m")
    data = np.random.randint(0, 255, (2, 512, 512), dtype=np.uint8)
    with tifffile.TiffWriter(str(path), ome=True, bigtiff=True) as tif:
        tif.write(
            data,
            metadata={"Creator": "Ashlar v1.19.0", "Pixels": pixels},
            subifds=2, tile=(256, 256), photometric="minisblack",
            compression="adobe_deflate", predictor=True,
        )
        for level in (2, 4):
            tif.write(
                data[:, ::level, ::level], subfiletype=1, tile=(256, 256),
                photometric="minisblack", compression="adobe_deflate", predictor=True,
            )


def _pixels(path):
    with tifffile.TiffFile(str(path)) as tif:
        xml_str = tif.ome_metadata
        series = tif.series[0]
        axes, shape = series.axes, series.shape
    root = ET.fromstring(xml_str)
    ns = re.match(r"\{.*\}", root.tag).group(0)
    return xml_str, root.find(f".//{ns}Pixels"), axes, shape


def test_inject_leaves_correct_description_untouched(tmp_path):
    out = tmp_path / "slide.ome.tif"
    _write_ashlar_style(out)
    before = tifffile.tiffcomment(str(out))
    inject_physical_size(str(out), PIXEL_SIZE)
    assert tifffile.tiffcomment(str(out)) == before


def test_inject_on_ashlar_style_output_keeps_channels(tmp_path):
    out = tmp_path / "slide.ome.tif"
    _write_ashlar_style(out)
    inject_physical_size(str(out), PIXEL_SIZE)
    xml_str, pixels, _, _ = _pixels(out)
    assert "&#" not in xml_str
    assert float(pixels.get("PhysicalSizeX")) == pytest.approx(PIXEL_SIZE)
    assert float(pixels.get("PhysicalSizeY")) == pytest.approx(PIXEL_SIZE)
    assert pixels.get("SizeC") == "2"
    assert pixels.get("SizeT") == "1"


def test_inject_rewrite_branch_strips_units_without_char_refs(tmp_path):
    """Description lacks the declared size and carries a literal µm unit: the
    rewrite must drop the unit attributes and never emit '&#181;'."""
    out = tmp_path / "slide.ome.tif"
    _write_ashlar_style(out, unit_attrs=True, size=0.5)
    xml = tifffile.tiffcomment(str(out))
    assert "\u00b5m" in xml  # literal µm, as tifffile/ashlar write it
    assert 'PhysicalSizeX="0.5"' in xml
    inject_physical_size(str(out), PIXEL_SIZE)
    xml_str, pixels, _, _ = _pixels(out)
    assert "&#" not in xml_str
    assert "PhysicalSizeXUnit" not in xml_str and "PhysicalSizeYUnit" not in xml_str
    assert float(pixels.get("PhysicalSizeX")) == pytest.approx(PIXEL_SIZE)
    assert float(pixels.get("PhysicalSizeY")) == pytest.approx(PIXEL_SIZE)
    assert pixels.get("SizeC") == "2" and pixels.get("SizeT") == "1"


def test_inject_rewrite_branch_with_missing_size(tmp_path):
    out = tmp_path / "slide.ome.tif"
    _write_ashlar_style(out, size=None)
    inject_physical_size(str(out), PIXEL_SIZE)
    xml_str, pixels, _, _ = _pixels(out)
    assert "&#" not in xml_str
    assert float(pixels.get("PhysicalSizeX")) == pytest.approx(PIXEL_SIZE)
    assert pixels.get("SizeC") == "2"


def test_rewrite_text_edit_never_reserializes():
    from src.utils.stitching_utils import _rewrite_calibration
    xml = ('<OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06"><Image><Pixels ID="P" '
           'PhysicalSizeX="0.1" PhysicalSizeXUnit="\u00b5m" PhysicalSizeY="0.1" '
           'PhysicalSizeYUnit="\u00b5m" SizeC="2"/><Note>\u00b5m</Note></Image></OME>')
    out = _rewrite_calibration(xml, 0.63)
    assert "&#" not in out
    assert "Unit" not in out
    assert 'PhysicalSizeX="0.63"' in out and 'PhysicalSizeY="0.63"' in out
    assert 'SizeC="2"' in out


def test_verify_fails_on_character_reference(tmp_path):
    from src.utils.stitching_utils import _verify_physical_size
    out = tmp_path / "slide.ome.tif"
    _write_ashlar_style(out)
    xml = tifffile.tiffcomment(str(out)).replace("\u00b5m", "&#181;m")
    tifffile.tiffcomment(str(out), xml)
    with pytest.raises(RuntimeError, match="&#"):
        _verify_physical_size(str(out), PIXEL_SIZE)


SAMPLE_TILES = Path(__file__).resolve().parent.parent / "sample_data" / "output"


@pytest.mark.skipif(not shutil.which("ashlar"), reason="ashlar CLI not installed")
@pytest.mark.skipif(len(list(SAMPLE_TILES.glob("TileScan_001_s*_ch00.tif"))) != 9,
                    reason="sample tiles not available")
def test_stitching_step_two_channel_end_to_end(tmp_path):
    from src.config.schema import StitchingConfig
    from src.steps.stitching import StitchingStep

    for src in SAMPLE_TILES.glob("TileScan_001_s*_ch00.tif"):
        shutil.copy(src, tmp_path / src.name)
        shutil.copy(src, tmp_path / src.name.replace("_ch00", "_ch01"))

    config = StitchingConfig(
        pattern="TileScan_001_s{series:3}_ch{channel:2}.tif",
        width=3, height=3, overlap=0.1008, pixel_size=0.63,
        layout="raster", direction="vertical",
    )
    result = StitchingStep(config).run(str(tmp_path))

    xml_str, pixels, _, _ = _pixels(result.data)
    assert pixels.get("SizeC") == "2"
    assert pixels.get("SizeT") == "1"
    assert "&#" not in xml_str
    assert float(pixels.get("PhysicalSizeX")) == pytest.approx(0.63)
    assert float(pixels.get("PhysicalSizeY")) == pytest.approx(0.63)
