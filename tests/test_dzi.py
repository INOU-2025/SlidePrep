"""Tests for DZI pyramid generation via libvips (skipped when vips is absent)."""

import shutil
import subprocess

import numpy as np
import pytest
import tifffile


@pytest.mark.skipif(not shutil.which("vips"), reason="vips not installed")
def test_dzi_generates_files(tmp_path):
    src = tmp_path / "slide.tif"
    tifffile.imwrite(str(src), np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8))

    out = str(tmp_path / "panorama")
    subprocess.run(["vips", "dzsave", str(src), out], check=True)

    assert (tmp_path / "panorama.dzi").exists()
    assert (tmp_path / "panorama_files").is_dir()
