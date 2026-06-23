# SlidePrep — Microscopy Image Processing Pipeline

A modular, production-ready pipeline for generating high-quality Whole Slide Images (WSI) from microscopy image tiles. Supports two operating modes: full preprocessing (grid-artifact removal via LaMa inpainting, then stitching) for counting-chamber tiles, and passthrough mode (`--no-grid`) for clean tiles that need only stitching and DZI generation.

Optimized for thick grid detection (21 px lines, ~2° rotation) with cellular content preservation.

---

## Usage modes

SlidePrep supports two independent usage modes that share the same pipeline core:

| Mode | Entry point | When to use |
|---|---|---|
| **CLI** | `main.py` | Batch processing on a local machine |
| **Web** | FastAPI + Celery + Angular | Multi-user server deployment |

---

## Sample data

A real 3×3 tile set is committed under `sample_data/tiles/` — a subset of the development dataset acquired from a Sedgwick-Rafter counting chamber. The accompanying `sample_data/config.json` is pre-configured for this tile set.

```bash
# Full pipeline: grid removal → stitching
python main.py sample_data/config.json \
    --input  sample_data/tiles \
    --output sample_data/output
```

The mussel larvae images used as sample data were kindly provided by África González Fernández, Andrea Hernández Fernández, and Silvia Lorenzo Abalde (IN1 Immunology Group, CINBIO, University of Vigo). The images were acquired within the project *"Identificación e marcaxe selectiva de larvas de mexillón mediante anticorpos monoclonais"*, supported by the European Maritime, Fisheries and Aquaculture Fund (EMFAF) and Consellería do Mar, Xunta de Galicia.

---

## Quick start

### CLI

**1. Name your tile files** to match the `stitching.pattern` in the config (default: `TileScan_001_s{series:3}_ch{channel:2}.tif`). Each tile gets a zero-padded series index assigned in column-major order:

```
tiles/
  TileScan_001_s000_ch00.tif   ← column 0, row 0
  TileScan_001_s001_ch00.tif   ← column 0, row 1
  TileScan_001_s002_ch00.tif   ← column 0, row 2
  TileScan_001_s003_ch00.tif   ← column 1, row 0
  ...
```

**2. Set your paths and grid size** in `config/production.json`:

```json
"general":  { "input_path": "/path/to/tiles", "output_path": "/path/to/output" },
"stitching": { "width": 14, "height": 49, "overlap": 0.1, "pixel_size": 0.324957 }
```

`width` × `height` must equal the total number of tiles. `pixel_size` is in µm/pixel (check your microscope's acquisition log).

**3. Run:**

```bash
python main.py config/production.json
```

### Web (Docker Compose)

**CPU (default):**
```bash
docker compose up --build
```

**GPU (Linux + NVIDIA):**
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

The GPU override adds an NVIDIA device reservation to the Celery worker so it can use CUDA at runtime. PyTorch falls back to CPU automatically when the GPU override is not used.

> **GPU prerequisite:** the NVIDIA Container Toolkit must be installed on the host before using the GPU override:
> ```bash
> sudo apt install nvidia-container-toolkit
> sudo systemctl restart docker
> ```

Both commands build and start four services: a Redis broker, the FastAPI backend (port 8000), a Celery worker, and an nginx container that serves the pre-built Angular frontend. Open `http://localhost` in your browser — no Node.js installation required. From another machine on the same network, use `http://<server-ip>` instead.

---

## Pipeline

### Full pipeline (default)

Each image passes through six steps in sequence:

| # | Step | Description |
|---|---|---|
| 1 | **Binarization** | Converts the tile to binary using the Combined Differential method |
| 2 | **Grid Detection** | Adaptive template matching to locate grid lines |
| 3 | **Grid Refinement** | Classifier-based contour filtering and thickness adjustment |
| 4 | **Mask Creation** | Renders refined contours into a binary inpainting mask |
| 5 | **Inpainting** | Removes masked grid regions using LaMa |
| 6 | **Image Conversion** | Converts to the configured output format and colour mode |

### Passthrough pipeline (`--no-grid`)

Steps 1–5 are skipped entirely. Each tile passes only through **Image Conversion** (step 6) for format normalisation, then proceeds directly to stitching. Use this mode when tiles are already free of grid artifacts.

### Stitching (both modes)

After all tiles are processed, **Stitching** (`StitchingStep`) runs once on the output folder to produce a single OME-TIFF via Ashlar. It runs outside the per-image pipeline because it operates on the full tile set.

After Ashlar writes the file, SlidePrep patches the embedded OME-XML to set `PhysicalSizeX` and `PhysicalSizeY` (in µm) from `stitching.pixel_size` in your configuration. This ensures that bioimage analysis tools — QuPath, FIJI, napari, CellProfiler — read calibrated physical units instead of raw pixels for any downstream measurement.

---

## Project structure

```
SlidePrep/
├── main.py                        # CLI entry point
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── environment.yml
│
├── api/                           # FastAPI web service
│   ├── app.py                     # Application factory, CORS, static mounts
│   ├── routes.py                  # /jobs endpoints (create, status, delete)
│   └── schemas.py                 # Pydantic request/response models
│
├── worker/                        # Celery async worker
│   ├── celery_app.py
│   └── tasks.py                   # process_images_task
│
├── client/                        # Angular frontend (Angular 19, standalone components)
│   └── src/app/
│       ├── core/services/         # ApiService, ProjectService
│       ├── shared/top-bar/        # App bar (home + workspace modes)
│       ├── features/startup/      # Slide list + two-step create-slide modal
│       └── features/workspace/    # Deep-zoom viewer (OpenSeadragon)
│
├── config/                        # JSON configuration files
│   ├── production.json
│   ├── development.json
│   └── test/                      # Per-step test configurations
│
├── scripts/                       # Individual step test runners
│   ├── test_runner.py             # StepTestRunner harness
│   ├── test_binarization.py
│   ├── test_detection.py
│   ├── test_adaptive_detection.py
│   ├── test_detection_refinement.py
│   ├── test_mask_creation.py
│   ├── test_inpainting.py
│   ├── test_img_conversion.py
│   └── test_stitching.py
│
├── src/
│   ├── config/                    # Pydantic configuration schemas
│   │   └── schema.py
│   ├── core/                      # Pipeline engine and DI container
│   │   ├── bootstrap.py           # Container factory
│   │   ├── container.py           # Dependency injection container
│   │   ├── pipeline.py            # Sequential step executor
│   │   ├── pipeline_service.py    # High-level service + build_default_pipeline
│   │   ├── step.py                # PipelineStep base class
│   │   ├── step_result.py         # StepResult domain object
│   │   ├── app_config_manager.py  # Typed config accessor
│   │   ├── context.py             # Shared per-image runtime state
│   │   ├── logger.py
│   │   └── debugger.py
│   ├── steps/                     # Step implementations
│   │   ├── binarization.py
│   │   ├── grid_detection.py
│   │   ├── grid_refinement.py
│   │   ├── mask_creation.py
│   │   ├── inpainting.py
│   │   ├── img_conversion.py
│   │   └── stitching.py
│   └── utils/
│       ├── binarization/          # Thresholding method implementations
│       ├── detection/             # Adaptive detector, contour analysis
│       ├── debug/                 # Visualization and result writers
│       ├── image_utils.py
│       └── conversion_utils.py
│
├── models/
│   └── rf_detection_classifier.joblib   # Grid refinement classifier
│
├── docs/                          # Extended documentation
└── training/                      # RF classifier retraining script (see "Adapting the classifier")
```

---

## Installation

### Prerequisites

**Java (JDK)** is required by Ashlar for OME-TIFF stitching. Install it before creating the environment:

- macOS: `brew install openjdk`
- Ubuntu/Debian: `sudo apt install default-jdk`

### Conda (recommended)

**macOS (CPU / Apple Silicon MPS):**
```bash
conda env create -f environment.yml -n slideprep
conda activate slideprep
pip install --no-deps simple-lama-inpainting==0.1.2
```

**Linux (CPU):**

> **GCC 14+ note:** Pillow 9.5.0 fails to build on systems with GCC 14 or newer. Export this flag before creating the environment:
> ```bash
> export CFLAGS="-Wno-error=incompatible-pointer-types"
> ```

```bash
conda env create -f environment.yml -n slideprep
conda activate slideprep
pip install --no-deps simple-lama-inpainting==0.1.2
```

**Linux with NVIDIA GPU (CUDA):**

> **GCC 14+ note:** same as above — set `CFLAGS` before creating the environment if your system has GCC 14 or newer.

```bash
conda env create -f environment-cuda.yml -n slideprep
conda activate slideprep
pip install --no-deps simple-lama-inpainting==0.1.2
```

> `simple-lama-inpainting==0.1.2` declares `pillow<10` in its metadata, which conflicts with the `pillow>=10` required elsewhere. Installing it with `--no-deps` bypasses the metadata check; its runtime dependencies (torch, pillow, numpy) are already satisfied by the environment.

### pip

```bash
pip install -r requirements.txt
```

---

## CLI usage

```bash
# Run the full pipeline on a folder of tiles (grid removal + stitching)
python main.py config/production.json

# Skip grid removal — stitching and DZI generation only (clean tiles)
python main.py config/production.json --no-grid

# Use a custom config
python main.py path/to/config.json
```

Processed tiles are written to `general.output_path`. Stitching produces an OME-TIFF in the same directory.

### Programmatic use

```python
import cv2
from src.core.pipeline_service import PipelineService

gray = cv2.imread("tile.png", cv2.IMREAD_GRAYSCALE)
service = PipelineService("config/production.json")
result = service.run(gray, image_path="tile.png")
output = result.image        # numpy ndarray
metadata = result.metadata   # dict with format/mode keys
```

### Custom pipeline assembly

```python
from src.core.pipeline_service import PipelineService, build_default_pipeline
from src.core.pipeline import Pipeline
from src.steps import BinarizationStep, ImgConversionStep

def my_pipeline(config, container):
    return Pipeline([
        BinarizationStep(config=config.binarization_config),
        ImgConversionStep(config=config.img_conversion_config),
    ], container)

service = PipelineService("config/production.json", pipeline_factory=my_pipeline)
```

---

## Web usage

### Docker Compose (recommended)

```bash
docker-compose up --build
```

Builds and starts four services: Redis, the FastAPI backend (port 8000), a Celery worker, and an nginx container (port 80) serving the pre-built Angular app. Open `http://localhost` in your browser (or `http://<server-ip>` from another machine on the same network). Uploads and results are stored under `data/`.

### Manual startup (development)

For iterative frontend development, run the backend stack with Docker Compose and serve the Angular app locally:

```bash
# Start the backend stack
docker-compose up redis api worker

# In a separate terminal — Angular dev server (requires Node.js)
cd client
npm install
ng serve          # http://localhost:4200
```

Set `CORS_ORIGINS=http://localhost:4200` on the `api` service (or in a `.env` file) when using the Angular dev server instead of the nginx container.

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker URL |
| `SLIDEPREP_CONFIG` | `config/production.json` | Config file used by the worker |
| `CORS_ORIGINS` | `http://localhost` | Comma-separated allowed origins |

---

## Test suite

```bash
pytest tests/ -v
```

Ten tests covering config parsing, pipeline factory and step chaining, binarization on synthetic images, inpainting (LaMa model mocked), OME-TIFF physical calibration injection, and DZI generation. The DZI test is skipped automatically when `vips` is not installed.

---

## Individual step testing

Each step can be run and debugged in isolation using the `StepTestRunner` harness:

```bash
python scripts/test_binarization.py        config/test/binarization.json
python scripts/test_detection.py           config/test/grid_detection.json
python scripts/test_adaptive_detection.py  config/test/grid_detection.json
python scripts/test_detection_refinement.py config/test/grid_refinement.json
python scripts/test_mask_creation.py       config/test/mask_creation.json
python scripts/test_inpainting.py          config/test/inpainting.json
python scripts/test_img_conversion.py      config/test/img_conversion.json
python scripts/test_stitching.py           config/test/stitching.json
```

The runner injects a shared container into each step before execution, so steps that require pipeline context (image shape, original image, inpainting model) work identically to how they run inside the full pipeline.

---

## Adapting the classifier to a new chamber type

The grid-refinement step uses a Random Forest classifier (`models/rf_detection_classifier.joblib`) to distinguish true grid-line contours from false positives. The shipped model was trained on Sedgwick-Rafter chamber images. If it underperforms on a different chamber geometry, retrain it in three steps:

**1. Generate the feature CSV.** Enable debug output in your config and run the pipeline on 5–10 representative tiles:

```json
"debug": { "save_aggregated_data": true, "saved_artifact_type": "data",
           "result_file_name": "rf-data.csv" }
```

The grid detection step writes one row per detected contour, with columns `aspect_ratio`, `long_side_angle`, `corner_proximity`, `area`, `length`, and `orientation_mismatch`.

**2. Label the CSV.** Open `rf-data.csv` and add an `is_detection` column — `TRUE` for contours that are real grid lines, `FALSE` for false positives. A few hundred labelled rows is typically sufficient.

**3. Retrain and replace the model.**

```bash
python training/train_rf_detection_classifier.py --infile rf-data.csv
# Writes the new model to models/rf_detection_classifier.joblib automatically
```

Pass `--balanced` if grid-line contours are heavily outnumbered by background detections in your data. The training script uses 5-fold cross-validated grid search and prints a holdout classification report so you can verify accuracy before deploying the new model.

---

## Configuration

All parameters are set via JSON configuration files. The top-level sections map directly to typed Pydantic models in `src/config/schema.py`:

```json
{
  "general":        { "input_path": "...", "output_path": "...", "output_suffix": "" },
  "binarization":   { "threshold_method": "combined_differential" },
  "grid_detection": { "template_size": 21, "rotation_range": [-5, 5] },
  "grid_refinement":{ "target_thickness": 21, "thickness_bias": 0.8 },
  "inpainting":     { "model": "lama" },
  "img_conversion": { "format": "tiff", "mode": "RGB" },
  "stitching":      { "pattern": "...", "width": 0, "height": 0, "pixel_size": 1.0 },
  "log":            { "relative_path": "pipeline.log" },
  "debug":          { "enabled": false }
}
```

See `config/production.json` and `config/development.json` for full examples. Per-step test configs are in `config/test/`.

---

## Binarization methods

The pipeline uses **Combined Differential** by default. All seven methods are available directly for research use:

```python
from src.utils.binarization import BinarizationMethods

methods = BinarizationMethods()
binary = methods.apply_combined_differential_threshold(gray)
```

Available methods: `global_threshold`, `otsu`, `adaptive`, `multi_otsu`, `line_enhanced`, `morphological`, `combined_differential`.

---

## Documentation

Extended guides are in the [`docs/`](docs/) folder:

- [docs/SYSTEM_OVERVIEW.md](docs/SYSTEM_OVERVIEW.md) — Architecture and data flow
- [docs/BINARIZATION_METHODS_GUIDE.md](docs/BINARIZATION_METHODS_GUIDE.md) — Method comparison and selection
- [docs/CONFIGURATION_GUIDE.md](docs/CONFIGURATION_GUIDE.md) — Full configuration reference
- [docs/DEBUG_SYSTEM_GUIDE.md](docs/DEBUG_SYSTEM_GUIDE.md) — Debug visualisation
- [docs/LOGGING_CONFIGURATION.md](docs/LOGGING_CONFIGURATION.md) — Logging setup

---

## Credits

**Authors**

| Name | Affiliation |
|---|---|
| Ivan Rodriguez-Conde | ESEI · Universidade de Vigo |
| Celso Campos | ESEI · Universidade de Vigo |
| Florentino Fdez-Riverola | ESEI · Universidade de Vigo · SING Research Group, IIS Galicia Sur (SERGAS-UVIGO) |

**Contact** [ivarodriguez@uvigo.gal](mailto:ivarodriguez@uvigo.gal)

---

## License

MIT — see [LICENSE](LICENSE). A full audit of dependency licenses is available at [docs/LICENSE_AUDIT.md](docs/LICENSE_AUDIT.md); all dependencies use OSI-approved permissive licenses.
