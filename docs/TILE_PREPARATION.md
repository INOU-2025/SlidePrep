# Tile Preparation Guide

This guide covers everything you need before running SlidePrep: supported formats, how to name your tiles, how to set the grid dimensions, and how to verify your setup before committing to a long run.

---

## Supported file formats

SlidePrep accepts the following formats for input tiles:

| Format | Extensions |
|---|---|
| TIFF | `.tif`, `.tiff` |
| PNG | `.png` |
| JPEG | `.jpg`, `.jpeg` |
| BMP | `.bmp` |
| WebP | `.webp` |

Both lowercase and uppercase extensions are matched (e.g. `.TIF` and `.tif` are both found).

**Recommendation:** use multi-page or single-plane TIFF for fluorescence microscopy. JPEG is lossy and will degrade the fine detail the grid-detection step relies on.

---

## Tile naming

Ashlar (the stitching engine) requires tiles to follow a strict naming pattern. The default pattern is:

```
TileScan_001_s{series:3}_ch{channel:2}.tif
```

This means each filename encodes a **series index** (zero-padded to 3 digits) and a **channel index** (zero-padded to 2 digits):

```
TileScan_001_s000_ch00.tif   ← series 0, channel 0
TileScan_001_s001_ch00.tif   ← series 1, channel 0
TileScan_001_s002_ch00.tif   ← series 2, channel 0
...
```

You can use a different naming scheme by changing `stitching.pattern` in your config — any pattern with `{series:N}` and `{channel:N}` placeholders works. The `N` value controls the zero-padding width.

### Renaming tiles in bulk

If your microscope software exports files with different names, rename them before processing. The series index must be assigned in **column-major order** (see below).

---

## Grid layout and column-major ordering

SlidePrep uses a column-major tile ordering: series indices increment **down each column first**, then move to the next column.

For a 3 × 3 grid (`width=3`, `height=3`):

```
Column:   0           1           2
        ┌─────┐     ┌─────┐     ┌─────┐
Row 0   │ s000 │     │ s003 │     │ s006 │
        ├─────┤     ├─────┤     ├─────┤
Row 1   │ s001 │     │ s004 │     │ s007 │
        ├─────┤     ├─────┤     ├─────┤
Row 2   │ s002 │     │ s005 │     │ s008 │
        └─────┘     └─────┘     └─────┘
```

`width` is the number of **columns**, `height` is the number of **rows**.  
`width × height` must equal the total number of tile files.

### Checking the layout

Count your files and verify the product matches:

```bash
ls path/to/tiles/*.tif | wc -l   # should equal width × height
```

If the count is wrong, the stitching step will raise a `ValueError` and stop before doing any work.

---

## Setting `width` and `height`

In your config:

```json
"stitching": {
  "width": 14,
  "height": 49,
  ...
}
```

- `width` = number of tile columns in the acquisition grid
- `height` = number of tile rows in the acquisition grid

Check your microscope software's acquisition log — it will record the grid dimensions and tile count. The values must be exact; rounding or guessing will produce a malformed OME-TIFF or a stitching error.

---

## Setting `pixel_size`

`stitching.pixel_size` is the physical size of one pixel in **micrometres (µm)**. It is used to write calibrated `PhysicalSizeX`/`PhysicalSizeY` metadata into the output OME-TIFF so that downstream tools (QuPath, FIJI, napari, CellProfiler) report measurements in real units.

Find the value in your microscope's acquisition log — it is typically labelled "pixel size", "image scale", or "µm/pixel". For the sample data included with this repository the value is `0.324957` µm/pixel.

```json
"stitching": {
  "pixel_size": 0.324957,
  ...
}
```

If you do not know the pixel size, leave it at the default (`1.0`) — stitching will succeed but measurements in downstream tools will be in raw pixels.

---

## Filtering tiles by suffix

If your acquisition folder contains tiles from multiple channels or staining rounds, use `general.suffix_filter` to restrict processing to one subset:

```json
"general": {
  "suffix_filter": "_ch00"
}
```

Only files whose base name (without extension) ends with `_ch00` will be processed. All other files are silently ignored by the pipeline but remain on disk.

Leave `suffix_filter` as an empty string `""` to process every supported image in the folder.

---

## Tile overlap

`stitching.overlap` is the fractional overlap between adjacent tiles — typically set by the microscope's acquisition protocol. A value of `0.1` means each tile overlaps its neighbours by 10 % of its width/height. Ashlar uses this for registration.

```json
"stitching": {
  "overlap": 0.1
}
```

If registration fails or tiles appear misaligned in the output, try adjusting this value ± 0.05 to match your actual acquisition overlap.

---

## Raster direction

`stitching.direction` tells Ashlar how the stage traversed the grid:

| Value | Meaning |
|---|---|
| `"horizontal"` | The stage moved across rows, advancing one row at a time *(default)* |
| `"vertical"` | The stage moved down columns, advancing one column at a time |

Check your microscope software's acquisition settings if you are unsure. A wrong direction will cause checkerboard artefacts in the stitched output.

---

## Pre-flight checklist

Before starting a full pipeline run, verify:

- [ ] All tile files follow the naming pattern in `stitching.pattern`
- [ ] `ls *.tif | wc -l` equals `width × height`
- [ ] `pixel_size` has been read from the acquisition log
- [ ] `suffix_filter` is set if the folder contains mixed channels
- [ ] `direction` matches the microscope acquisition direction
- [ ] `output_path` exists and has write permission (`mkdir -p output_path`)
- [ ] Java is on `PATH` (required by Ashlar): `java -version`

### Quick smoke test

Run the pipeline on the 3 × 3 sample tiles first to confirm end-to-end connectivity before processing your full dataset:

```bash
python main.py sample_data/config.json \
    --input  sample_data/tiles \
    --output sample_data/output
```

---

## Related documentation

- [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) — full reference for `stitching`, `general`, and all other config sections
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — what to do when tiles are not found, Ashlar fails, or the output looks wrong
