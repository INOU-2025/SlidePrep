"""Helpers for StitchingStep: OME-XML calibration and the mosaic-space inpaint mask."""

from __future__ import annotations

import math
import os
import re
import xml.etree.ElementTree as ET
from typing import Any, Optional

import cv2
import numpy as np
import tifffile
from ashlar import reg, utils as ashlar_utils
from ashlar.fileseries import FileSeriesReader


def _parse_pixels(xml_str: str) -> tuple[ET.Element, str, list[ET.Element]]:
    """Parses an OME-XML document and finds every ``<Pixels>`` element,
    handling both a default namespace (``xmlns="..."``) and the
    namespace-less case. Returns ``(root, ns, pixels_elements)`` — shared
    between the write path and the post-write verification so both agree on
    what counts as "found", and so the write path can mutate/re-serialize
    the same root it just found elements in."""
    ns_match = re.search(r'xmlns="([^"]*)"', xml_str)
    ns = ns_match.group(1) if ns_match else ''
    ns_prefix = f'{{{ns}}}' if ns else ''
    root = ET.fromstring(xml_str)
    return root, ns, list(root.iter(f'{ns_prefix}Pixels'))


def _verify_physical_size(path: str, expected_um: float) -> None:
    """Re-reads the OME-XML just written and confirms PhysicalSizeX/Y
    actually landed. Raises RuntimeError naming the expected value, what was
    found (or absent), and the file path — a mosaic without correct
    calibration is a wrong result, not a degraded one, so this never logs a
    warning and continues.
    """
    with tifffile.TiffFile(path) as tif:
        xml_str = tif.ome_metadata

    found_x = found_y = None
    if xml_str:
        _, _, pixels_elements = _parse_pixels(xml_str)
        if pixels_elements:
            found_x = pixels_elements[0].get('PhysicalSizeX')
            found_y = pixels_elements[0].get('PhysicalSizeY')

    def matches(found: str | None) -> bool:
        if found is None:
            return False
        try:
            return math.isclose(float(found), expected_um, rel_tol=1e-9)
        except ValueError:
            return False

    if not (matches(found_x) and matches(found_y)):
        raise RuntimeError(
            f"Physical size verification failed for {path}: expected PhysicalSizeX/Y={expected_um}, "
            f"found PhysicalSizeX={found_x!r} PhysicalSizeY={found_y!r} after write."
        )


def inject_physical_size(path: str, pixel_size_um: float) -> None:
    """Patch PhysicalSizeX/Y calibration into an existing OME-TIFF in-place,
    then re-read the file to confirm the value actually landed.

    Raises RuntimeError (or whatever tifffile/ElementTree raise for a
    genuinely unreadable/malformed file) on any failure — including cases
    that would otherwise complete without having written anything: a
    namespace mismatch or a missing ``<Pixels>`` element both used to
    silently no-op the XML mutation while still "succeeding". A mosaic
    without correct calibration is a wrong result, not a degraded one, so
    nothing here logs a warning and continues.
    """
    xml_str = tifffile.tiffcomment(path)
    if not xml_str:
        raise RuntimeError(f"No OME-XML metadata found in {path} — cannot inject physical size calibration.")

    root, ns, pixels_elements = _parse_pixels(xml_str)
    if not pixels_elements:
        raise RuntimeError(f"No <Pixels> element found in OME-XML metadata of {path} — cannot inject physical size calibration.")

    for pixels in pixels_elements:
        pixels.set('PhysicalSizeX', str(pixel_size_um))
        pixels.set('PhysicalSizeY', str(pixel_size_um))
        pixels.set('PhysicalSizeXUnit', 'µm')
        pixels.set('PhysicalSizeYUnit', 'µm')

    if ns:
        ET.register_namespace('', ns)
    # ASCII encoding replaces µ (U+00B5) with &#181; — valid XML that OME readers decode correctly.
    # tifffile requires 7-bit ASCII for the ImageDescription tag.
    tifffile.tiffcomment(path, ET.tostring(root, encoding='ascii').decode('ascii'))

    _verify_physical_size(path, pixel_size_um)


def compose_mosaic_mask(
    mosaic_shape: tuple[int, int],
    tile_masks: list[tuple[np.ndarray, tuple[float, float]]],
) -> np.ndarray:
    """Composite per-tile masks into mosaic space using Ashlar's own placement.

    Each tile mask is pasted at its tile's absolute mosaic-pixel position
    using :func:`ashlar.utils.paste`, the same primitive Ashlar uses to
    composite pixel data (identical sub-pixel shift/clipping behaviour). The
    combine function is ``np.maximum`` rather than Ashlar's own blend, since
    a binary mask must OR across overlaps ("any reconstructed contribution
    marks the pixel reconstructed"), not average intensities.

    Args:
        mosaic_shape: (height, width) of the mosaic canvas, e.g.
            ``EdgeAligner.mosaic_shape``.
        tile_masks: (mask_array, (row, col)) pairs. ``mask_array`` uses
            ``MaskCreationStep``'s convention (0=observed, nonzero=
            reconstructed); ``(row, col)`` is the tile's absolute mosaic-pixel
            position, e.g. ``EdgeAligner.positions[i]``.

    Returns:
        uint8 array of shape ``mosaic_shape``; 255=reconstructed, 0=observed
        (full-range binary values so the file also renders correctly in a
        plain viewer with no contrast stretching, matching the 0/255
        convention already used by ``MaskCreationStep`` and the per-tile
        sidecars).
    """
    canvas = np.zeros(mosaic_shape, dtype=np.uint8)
    for mask, position in tile_masks:
        binary = (np.asarray(mask) > 0).astype(np.uint8) * 255
        ashlar_utils.paste(canvas, binary, position, func=np.maximum)
    # ashlar.utils.paste cubic-spline-interpolates tiles at non-integer
    # positions (its sub-pixel shift), which can leave intermediate values
    # along mask edges. Re-threshold so the output stays strictly binary.
    return np.where(canvas > 127, 255, 0).astype(np.uint8)


def mosaic_mask_path(ome_tiff_path: str) -> str:
    """Derive `<mosaic_base>_inpaint_mask.tif` from the OME-TIFF's own path."""
    base = re.sub(
        r"(\.ome)?\.tiff?$", "", os.path.basename(ome_tiff_path), flags=re.IGNORECASE
    )
    return os.path.join(os.path.dirname(ome_tiff_path), f"{base}_inpaint_mask.tif")


def write_inpaint_mask(tile_dir: str, ome_tiff_path: str, config: Any) -> Optional[str]:
    """Compose and write the mosaic-space inpaint mask, if any tiles have one.

    Runs a second, in-process Ashlar registration pass — deterministic and
    built from the same fileseries config ``StitchingStep`` already used for
    its OME-TIFF-producing subprocess call — purely to obtain per-tile
    placement for mask compositing, without touching that existing codepath.
    Writes nothing (and skips registration entirely) when no per-tile mask
    sidecars exist for this job, e.g. when ``--no-grid`` was used and grid
    removal never ran.

    Args:
        tile_dir: Directory of processed tiles ``StitchingStep`` just stitched.
        ome_tiff_path: Path ``StitchingStep`` wrote the OME-TIFF to.
        config: The job's ``StitchingConfig``.

    Returns:
        The path the mask was written to, or ``None`` if nothing was written.
    """
    mask_dir = os.path.join(tile_dir, "inpaint_masks")
    if not os.path.isdir(mask_dir) or not os.listdir(mask_dir):
        return None

    reader = FileSeriesReader(
        tile_dir,
        pattern=config.pattern,
        overlap=config.overlap,
        width=config.width,
        height=config.height,
        layout=config.layout,
        direction=config.direction,
        pixel_size=config.pixel_size,
    )
    channel = config.align_channel if config.align_channel is not None else 0
    aligner = reg.EdgeAligner(
        reader,
        channel=channel,
        max_shift=config.max_shift,
        alpha=0.01,
        max_error=None,
        filter_sigma=0.0,
        do_make_thumbnail=False,
    )
    aligner.run()

    metadata_reader = reader.metadata
    tile_masks: list[tuple[np.ndarray, tuple[float, float]]] = []
    for i, position in enumerate(aligner.positions):
        for c in metadata_reader.channel_map:
            fname = metadata_reader.filename(i, c)
            stem = os.path.splitext(fname)[0]
            candidate = os.path.join(mask_dir, f"{stem}.png")
            if os.path.exists(candidate):
                mask_array = cv2.imread(candidate, cv2.IMREAD_GRAYSCALE)
                tile_masks.append((mask_array, tuple(position)))
                break  # at most one channel is grid-cleaned per series

    if not tile_masks:
        return None

    canvas = compose_mosaic_mask(tuple(aligner.mosaic_shape), tile_masks)
    mask_path = mosaic_mask_path(ome_tiff_path)
    resolution_cm = 10000 / config.pixel_size
    tifffile.imwrite(
        mask_path,
        canvas,
        photometric="minisblack",
        resolution=(resolution_cm, resolution_cm),
        resolutionunit="CENTIMETER",
    )
    return mask_path
