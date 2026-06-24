# Troubleshooting

Common errors, their causes, and how to fix them. Errors are grouped by pipeline stage.

---

## Installation

### `pillow<10` conflict when installing `simple-lama-inpainting`

**Error:**
```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed...
simple-lama-inpainting 0.1.2 requires Pillow<10
```

**Cause:** `simple-lama-inpainting==0.1.2` declares an upper bound on Pillow that conflicts with the `pillow>=10` needed elsewhere in the environment.

**Fix:** Always install with `--no-deps`:
```bash
pip install --no-deps simple-lama-inpainting==0.1.2
```
Its runtime dependencies (torch, pillow, numpy) are already satisfied by the conda environment, so skipping metadata resolution is safe.

---

### `error: command '/usr/bin/gcc' failed` during `conda env create`

**Error:**
```
error: incompatible pointer types...
```

**Cause:** Pillow 9.5.0 fails to compile on systems with GCC 14 or newer.

**Fix:** Set the flag before creating the environment:
```bash
export CFLAGS="-Wno-error=incompatible-pointer-types"
conda env create -f environment.yml -n slideprep
```

---

### `java: command not found` or Ashlar raises `FileNotFoundError`

**Cause:** Ashlar requires a Java runtime on `PATH`. It is not installed by the conda environment.

**Fix:**
```bash
# macOS
brew install openjdk
echo 'export PATH="/opt/homebrew/opt/openjdk/bin:$PATH"' >> ~/.zshrc

# Ubuntu/Debian
sudo apt install default-jdk
```

Verify: `java -version` should print a version string without error.

---

## CLI startup

### `Input path does not exist: /path/to/tiles`

**Cause:** The `general.input_path` in the config does not point to an existing directory.

**Fix:** Set the correct absolute path in your config, or pass `--input path/to/tiles` on the command line to override:
```bash
python main.py config/production.json --input /correct/path/to/tiles
```

---

### `input_path must be specified in the general config section`

**Cause:** `general.input_path` is empty and no `--input` override was given.

**Fix:** Add the path to your config file:
```json
"general": { "input_path": "/path/to/tiles" }
```

---

### `No images found in /path/to/tiles`

**Cause:** No files with a supported extension (`.tif`, `.tiff`, `.png`, `.jpg`, `.jpeg`, `.bmp`, `.webp`) were found in `input_path`, or `suffix_filter` excludes all files.

**Fix:**
1. Confirm the folder contains supported image files: `ls /path/to/tiles/*.tif`
2. Check `general.suffix_filter` — if set, it must match the suffix of your tile filenames (without extension).
3. Check that extensions are lowercase; uppercase extensions (`.TIF`) are also matched but confirm with `ls`.

---

## Grid detection

### `No tiles found using pattern <glob> in <dir>`

**Cause:** The `stitching.pattern` does not match any files in the output folder when stitching is attempted.

**Fix:** Verify that `stitching.pattern` matches your output filenames exactly. The pattern `TileScan_001_s{series:3}_ch{channel:2}.tif` generates a glob `TileScan_001_s*_ch*.tif`. Run the glob manually to check:
```bash
ls output_dir/TileScan_001_s*_ch*.tif | head
```
If no files match, adjust `stitching.pattern` to reflect the actual names.

---

### Grid lines not removed / faint grid still visible

**Cause (a):** The `grid_detection.angles` list does not include the actual rotation angle of the grid.

**Fix:** Inspect a tile at high magnification and measure the grid angle. Add it (and its negative) to the `angles` list:
```json
"grid_detection": { "angles": [1.5, -1.5] }
```

**Cause (b):** The `grid_detection.threshold` is too high, causing the detector to miss weaker matches.

**Fix:** Lower the threshold (towards `0.05`) and re-run a step test:
```bash
python scripts/test_detection.py config/test/grid_detection.json
```

**Cause (c):** The classifier is rejecting true grid-line contours on a new chamber geometry.

**Fix:** Retrain the Random Forest classifier. See *Adapting the classifier* in the main README.

---

### `width × height` mismatch

**Error:** Ashlar exits with an error about tile count or the stitched output is misaligned.

**Cause:** `stitching.width × stitching.height` does not equal the actual number of processed tiles.

**Fix:**
```bash
ls output_dir/*.tif | wc -l   # compare against width × height in config
```
Adjust `width` and `height` to match the actual tile count.

---

## Inpainting

### LaMa model fails to load / `RuntimeError: CUDA out of memory`

**Cause (load failure):** `simple-lama-inpainting` was not installed, or was installed with `--no-deps` skipped after a failed environment creation.

**Fix:** Reinstall:
```bash
pip install --no-deps simple-lama-inpainting==0.1.2
```

**Cause (CUDA OOM):** The tile resolution exceeds available GPU memory.

**Fix options:**
- Reduce tile size at acquisition time.
- Force CPU inference by disabling CUDA:
  ```bash
  CUDA_VISIBLE_DEVICES='' python main.py config/production.json
  ```
- Use the `--cpu-only` flag with `benchmark_pipeline.py` to verify CPU operation.

---

## Stitching

### `ashlar: command not found`

**Cause:** Ashlar is not installed or not on `PATH`.

**Fix:** Ashlar is installed by the conda environment. If it is missing:
```bash
conda activate slideprep
pip install ashlar
```

Verify: `ashlar --version`

---

### Stitched output is blank / heavily misaligned

**Cause (a):** Wrong `stitching.direction`. The stage traversed columns before rows but `direction` is set to `"horizontal"`.

**Fix:** Switch to `"vertical"` and re-stitch:
```json
"stitching": { "direction": "vertical" }
```

**Cause (b):** `overlap` value is significantly wrong.

**Fix:** Measure the actual overlap from adjacent tiles in ImageJ/FIJI and update `stitching.overlap`.

---

### `PhysicalSizeX`/`PhysicalSizeY` missing in downstream tools

**Cause:** `stitching.pixel_size` is set to `1.0` (the default) or is incorrect.

**Fix:** Read the µm/pixel value from your microscope's acquisition log and set it in the config:
```json
"stitching": { "pixel_size": 0.324957 }
```
After re-running, verify in QuPath: *Image → Show image info* should show physical pixel size in µm.

---

## Web mode

### `redis.exceptions.ConnectionError`

**Cause:** The Redis broker is not running or `REDIS_URL` is wrong.

**Fix:** Start the full stack with Docker Compose rather than running services individually:
```bash
docker compose up
```

If running services manually, ensure Redis is running and `REDIS_URL` is set:
```bash
redis-server &
export REDIS_URL=redis://localhost:6379/0
```

---

### DZI generation fails / `vips: command not found`

**Cause:** `libvips` is not installed. It is bundled inside the Docker image but is not installed by the conda environment (DZI generation is web-only).

**Fix (Docker):** Rebuild the image:
```bash
docker compose up --build
```

**Fix (manual):**
```bash
# Ubuntu/Debian
sudo apt install libvips-tools

# macOS
brew install vips
```

Verify: `vips --version`

---

### Job stays in `QUEUED` state

**Cause:** The Celery worker is not running.

**Fix:** Start the worker:
```bash
# With Docker Compose (recommended)
docker compose up redis api worker

# Manually
celery -A worker.celery_app worker --loglevel=info
```

---

## Debug output

### Debug images not written

**Cause:** `general.debug` is `false` (the single source of truth for debug enablement).

**Fix:**
```json
"general": { "debug": true }
```

Also confirm the output directory is writable and `debug.saved_artifact_type` is set to `"image"` or `"both"`.

---

## Getting further help

1. Run with `log_level: "DEBUG"` and `log_to_console: true` to see per-step timing and diagnostic messages.
2. Use the step test scripts to isolate failures to a single step:
   ```bash
   python scripts/test_detection.py config/test/grid_detection.json
   ```
3. Open an issue at the project repository and include the full log output and your config file (with paths anonymised).
