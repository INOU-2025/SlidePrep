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
from ashlar.fileseries import FileSeriesReader, format_to_regex


def count_tile_positions(tile_paths: list[str], pattern: str) -> int:
    """Number of distinct (well, series) grid positions among ``tile_paths``,
    parsed via ashlar's own ``format_to_regex`` — the same parser ASHLAR
    itself uses for this pattern, so this can never disagree with how ASHLAR
    will interpret the same files. Channels collapse: a 2-channel
    acquisition's two files for the same position count as one position, not
    two — a raw file-count glob would count every channel separately.
    """
    name_regex = re.compile(format_to_regex(pattern))
    positions = set()
    for path in tile_paths:
        m = name_regex.match(os.path.basename(path))
        if m:
            gd = m.groupdict()
            positions.add((gd.get('well'), gd['series']))
    return len(positions)


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


_MICRON = "\u00b5m"
_PIXELS_TAG_RE = re.compile(r"<(?:[\w.-]+:)?Pixels\b[^>]*>")
_PHYSICAL_ATTR_RE = re.compile(r"\s+PhysicalSize[XY](?:Unit)?\s*=\s*(?:\"[^\"]*\"|'[^']*')")


def _close_to(found: str | None, expected_um: float) -> bool:
    """True if ``found`` parses as a float within rel_tol=1e-6 of ``expected_um``."""
    if found is None:
        return False
    try:
        return math.isclose(float(found), expected_um, rel_tol=1e-6)
    except ValueError:
        return False


def _is_calibrated(xml_str: str, expected_um: float) -> bool:
    """True if every ``<Pixels>`` carries the declared PhysicalSizeX/Y, any unit
    attribute is absent or a literal µm, and the text has no character
    references (``&#``) — which Bio-Formats rejects as OME-TIFF."""
    if "&#" in xml_str:
        return False
    _, _, pixels_elements = _parse_pixels(xml_str)
    if not pixels_elements:
        return False
    for pixels in pixels_elements:
        if not (_close_to(pixels.get('PhysicalSizeX'), expected_um)
                and _close_to(pixels.get('PhysicalSizeY'), expected_um)):
            return False
        for unit in ('PhysicalSizeXUnit', 'PhysicalSizeYUnit'):
            if pixels.get(unit) not in (None, _MICRON):
                return False
    return True


def _verify_physical_size(path: str, expected_um: float) -> None:
    """Re-reads the OME-XML and confirms PhysicalSizeX/Y are present, equal to
    the declared value, and that the description holds no ``&#`` character
    references. Raises RuntimeError naming the expected value, what was found
    (or absent), and the file path — a mosaic without correct calibration is a
    wrong result, not a degraded one, so this never logs a warning and
    continues. A literal µm unit is accepted.
    """
    with tifffile.TiffFile(path) as tif:
        xml_str = tif.ome_metadata

    found_x = found_y = None
    if xml_str:
        _, _, pixels_elements = _parse_pixels(xml_str)
        if pixels_elements:
            found_x = pixels_elements[0].get('PhysicalSizeX')
            found_y = pixels_elements[0].get('PhysicalSizeY')

    if not (_close_to(found_x, expected_um) and _close_to(found_y, expected_um)):
        raise RuntimeError(
            f"Physical size verification failed for {path}: expected PhysicalSizeX/Y={expected_um}, "
            f"found PhysicalSizeX={found_x!r} PhysicalSizeY={found_y!r} after write."
        )
    if "&#" in xml_str:
        raise RuntimeError(
            f"Physical size verification failed for {path}: the OME-XML description contains "
            "a character reference ('&#'), which Bio-Formats rejects as OME-TIFF "
            "(it falls back to the generic TIFF reader and misreads channels as timepoints)."
        )


def _rewrite_calibration(xml_str: str, pixel_size_um: float) -> str:
    """Returns ``xml_str`` with every ``<Pixels>`` start tag carrying only
    numeric PhysicalSizeX/Y (any PhysicalSize{X,Y}[Unit] attribute removed
    first). Edits the text in place rather than re-serializing, so literal
    characters elsewhere are never turned into ``&#NNN;`` references. OME
    defaults the unit to µm when the attribute is absent."""
    def patch(match: re.Match) -> str:
        tag = _PHYSICAL_ATTR_RE.sub("", match.group(0))
        name_end = re.match(r"<[^\s>/]+", tag).end()
        added = f' PhysicalSizeX="{pixel_size_um}" PhysicalSizeY="{pixel_size_um}"'
        return tag[:name_end] + added + tag[name_end:]

    return _PIXELS_TAG_RE.sub(patch, xml_str)


def inject_physical_size(path: str, pixel_size_um: float) -> None:
    """Ensure the OME-TIFF at ``path`` carries the declared pixel size.

    If the description already has PhysicalSizeX/Y equal to ``pixel_size_um``
    (Ashlar writes them itself from the ``pixel_size`` reader argument), the
    file is left untouched. Otherwise only numeric PhysicalSizeX/Y are
    written — no unit attributes and no character references, since
    Bio-Formats rejects a description containing ``&#181;m`` as OME-TIFF.
    The result is re-read to confirm.

    Raises RuntimeError (or whatever tifffile/ElementTree raise for a
    genuinely unreadable/malformed file) on any failure. A mosaic without
    correct calibration is a wrong result, not a degraded one, so nothing
    here logs a warning and continues.
    """
    xml_str = tifffile.tiffcomment(path)
    if not xml_str:
        raise RuntimeError(f"No OME-XML metadata found in {path} — cannot inject physical size calibration.")

    _, _, pixels_elements = _parse_pixels(xml_str)
    if not pixels_elements:
        raise RuntimeError(f"No <Pixels> element found in OME-XML metadata of {path} — cannot inject physical size calibration.")

    if not _is_calibrated(xml_str, pixel_size_um):
        new_xml = _rewrite_calibration(xml_str, pixel_size_um)
        # tifffile requires 7-bit ASCII for the ImageDescription tag.
        if not new_xml.isascii():
            raise RuntimeError(
                f"OME-XML of {path} contains non-ASCII text outside the physical-size "
                "attributes; tifffile cannot write it back without character references."
            )
        tifffile.tiffcomment(path, new_xml)

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
