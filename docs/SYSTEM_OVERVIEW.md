# SlidePrep System Overview

## 🧬 What is SlidePrep?

SlidePrep is a modular image processing pipeline designed to generate high-quality Whole Slide Images (WSI) from microscopy image tiles. It automatically detects and removes grid lines that appear during tile capture, then reconstructs the full slide using advanced stitching techniques.

## 🏗️ System Architecture

### Pipeline Stages

The per-image pipeline (`build_default_pipeline`) runs these six steps in sequence:

1. **Image Binarization** (`BinarizationStep`) - Convert to binary using Combined Differential thresholding ⭐ (grayscale conversion is handled internally)
2. **Grid Line Detection** (`GridDetectionStep`) - Detect horizontal and vertical grid patterns via template matching
3. **Detection Refinement** (`GridRefinementStep`) - Filter detections using a classifier and angle/thickness constraints
4. **Grid Mask Generation** (`MaskCreationStep`) - Create binary masks from refined detections
5. **Grid Removal / Inpainting** (`InpaintingStep`) - Remove grid artifacts using the LaMa inpainting model
6. **Image Conversion** (`ImgConversionStep`) - Convert processed images to the configured output format and color mode

After all images are processed, a seventh step runs once:

7. **Whole Slide Stitching** (`StitchingStep`) - Reconstruct the full slide from cleaned tiles (via Ashlar)

### Core Components

```
SlidePrep/
├── config/                 # JSON configuration files (production.json, development.json, test/)
├── docs/                   # Documentation and guides
├── scripts/                # Step-level test runners and validation scripts
├── src/                    # Source code
│   ├── config/             # Pydantic configuration schemas (schema.py)
│   ├── core/               # Core pipeline infrastructure
│   │   ├── pipeline.py         # Pipeline executor
│   │   ├── pipeline_service.py # High-level service and pipeline factory
│   │   ├── step.py             # PipelineStep base class
│   │   ├── step_result.py      # StepResult domain object
│   │   ├── bootstrap.py        # DI container factory
│   │   ├── app_config_manager.py # Typed config accessor
│   │   ├── container.py        # Dependency injection container
│   │   ├── context.py          # Per-image pipeline context
│   │   ├── logger.py           # Logging system
│   │   └── debugger.py         # Debug visualization system
│   ├── steps/              # Individual processing steps
│   │   ├── binarization.py     # Binary conversion
│   │   ├── grid_detection.py   # Grid pattern detection
│   │   ├── grid_refinement.py  # Post-process detection results
│   │   ├── mask_creation.py    # Binary mask generation
│   │   ├── inpainting.py       # LaMa-based grid removal
│   │   ├── img_conversion.py   # Output format conversion
│   │   └── stitching.py        # Ashlar-based slide assembly
│   └── utils/              # Utility modules
│       ├── binarization/   # Thresholding methods package
│       └── debug/          # Debug drawer classes
└── main.py                # CLI entry point
```

## 🎯 Production vs Research

### Production Use (Simplified)
The system is optimized for production with sensible defaults:

```python
from src.steps import BinarizationStep
from src.config import BinarizationConfig

# Simple production usage
config = BinarizationConfig()  # Uses combined_differential by default
step = BinarizationStep(config)
result = step.run(image_array)  # Returns StepResult
binary_image = result.to_array()
```

**Key Features**:
- **Combined Differential method** (21px thick grids, ~2° rotation)
- **Spurious element removal** (filters out cellular content)
- **Optimized parameters** (production-tested)
- **Minimal configuration** required

### Research Use (Comprehensive)
Full access to all methods for experimentation:

```python
from src.utils.binarization import BinarizationMethods, ThresholdMethod

methods = BinarizationMethods()
# Access all 7 methods: global, otsu, adaptive, multi_otsu, 
# line_enhanced, morphological, combined_differential
binary = methods.apply_method(ThresholdMethod.MULTI_OTSU, image)
```

**Key Features**:
- **7 different methods** with full parameter control
- **Batch evaluation script** (`src/utils/binarization/evaluate_binarization_methods.py`)
- **Debug callbacks** and detailed information
- **Comprehensive documentation** with examples

## 🔧 API Design Principles

### Direct Array Processing
Pipeline steps use direct numpy array processing for optimal performance and clarity:

```python
# Each step processes arrays directly and returns results
result = binarization_step.run(grayscale_image)   # returns StepResult
binary_image = result.to_array()                   # numpy ndarray
result = grid_detection_step.run(binary_image)
detections = result.data
metadata = result.metadata
```

### Type Safety (PEP 484)
All functions include comprehensive type hints for IDE support and static analysis:

```python
def run(self, data: Any) -> StepResult:
    """Process input with clear type contracts and return guarantees."""
```

### Professional Documentation (PEP 257)
Consistent docstring standards explain behavior and purpose:

```python
class BinarizationStep(PipelineStep):
    """Pipeline step for converting grayscale images to binary using thresholding methods.
    
    Applies configurable binarization algorithms to separate foreground from background,
    with automatic grayscale conversion for color inputs.
    """
```

### Configuration Validation
Automatic parameter validation with clear error messages:

```python
from pydantic import BaseModel, field_validator


class BinarizationConfig(BaseModel):
    threshold_method: str = "combined_differential"

    @field_validator("threshold_method")
    @classmethod
    def _validate_threshold_method(cls, value: str) -> str:
        # Comprehensive validation runs automatically
        return value
```

## ⚙️ Configuration System

### Typed Configuration
All components use typed configuration classes for safety and clarity:

```python
from src.config import BinarizationConfig

# Type-safe configuration
binarization_config = BinarizationConfig(
    threshold_method="combined_differential"
)

# GridDetectionConfig requires nested strategy dicts — load from JSON rather than
# constructing directly:
from src.core.app_config_manager import AppConfigManager
cfg_manager = AppConfigManager("config/production.json")
grid_config = cfg_manager.grid_detection_config
```

### Configuration Files
Default settings stored in JSON with schema validation:

```json
{
  "binarization": {
    "threshold_method": "combined_differential"
  },
  "grid_detection": {
    "threshold": 0.1,
    "angles": [-2.0],
    "general": { "template_length": 300, "thickness": 20, "min_contour_area": 100 },
    "thick_border": { "template_length": 60, "thickness": 7, "border_thickness": 30, "min_contour_area": 2 },
    "thin_border":  { "template_length": 30, "thickness": 7, "border_thickness": 20, "min_contour_area": 1 }
  }
}
```

## 🔧 Pipeline Architecture

The pipeline uses a **direct input-output function chaining** approach with **dependency injection**.
Each call to :func:`bootstrap` creates a new context-local container so
every worker or request gets an isolated registry:

```python
from src.core.bootstrap import bootstrap
from src.core.app_config_manager import AppConfigManager
from src.core.pipeline_service import build_default_pipeline

# Build a container for this task
cfg_manager = AppConfigManager(config_path)
container = bootstrap(config=cfg_manager)
cfg = container.resolve("config")

# Build and run the full default pipeline
pipeline = build_default_pipeline(cfg, container)
result = pipeline.run(input_image)
```

## 🐛 Debug and Visualization

### Debug System
Integrated debug output with automatic drawer integration:

```python
from src.core.bootstrap import bootstrap
from src.core.app_config_manager import AppConfigManager

cfg_manager = AppConfigManager(config_path)
container = bootstrap(config=cfg_manager)
cfg = container.resolve("config")
step = BinarizationStep(config=cfg.binarization_config)

# Automatic debug output when enabled:
result = step.run(image)
# Debugger automatically detects registered drawers and creates visualizations
```

### Test Runner Integration
Simplified testing with automatic debug output:

```python
from scripts.test_runner import StepTestRunner

runner = StepTestRunner(config_path)
step = GridDetectionStep(
    config=runner.cfg.grid_detection_config,
    debugger=runner.debugger,
    logger=runner.logger
)

# Process entire directory with automatic debug visualization
runner.run_on_directory(step, "grid_detection")
```

For each processed file, ``StepTestRunner`` searches ``general.input_path`` for
an image with the same filename and stores its path in the pipeline context.
This enables steps to load the original image even when their direct input is a
mask or other intermediate data. If ``test.input_type`` is ``"data"``, the
runner expects JSON files in ``test.input_path`` and pairs them with these
source images, refreshing the pipeline context for every file to emulate full
pipeline execution.

### Logging System
Comprehensive logging for monitoring and debugging:

```python
from io import StringIO
from src.config import LogConfig
from src.core.logger import Logger

log_cfg = LogConfig(log_to_file=True, stream=StringIO())
logger = Logger(log_cfg)
step = BinarizationStep(config, logger=logger)

# Logs processing time, parameters, and results
```

## 🧪 Testing and Validation

### Production Testing
Simple validation of the production method:

```bash
python scripts/test_binarization.py config/test/binarization.json
```

### Interactive Exploration
Batch evaluation of all binarization methods across a folder of images:

```bash
python src/utils/binarization/evaluate_binarization_methods.py path/to/config.json
```

### Grid Detection Testing
Validate grid detection separately:

```bash
python scripts/test_detection.py config/test/grid_detection.json
```

## 🎮 Usage Patterns

### Basic Pipeline Usage
```python
from src.core.bootstrap import bootstrap
from src.core.app_config_manager import AppConfigManager
from src.core.pipeline_service import build_default_pipeline

# Initialize application services
cfg_manager = AppConfigManager(config_path)
container = bootstrap(config=cfg_manager)
config = container.resolve("config")

# Build and run the full default pipeline
pipeline = build_default_pipeline(config, container)
result = pipeline.run(input_image)
```

### Individual Step Usage
```python
from src.core.bootstrap import bootstrap
from src.core.app_config_manager import AppConfigManager
from src.steps import BinarizationStep

# Initialize services first
cfg_manager = AppConfigManager(config_path)
container = bootstrap(config=cfg_manager)
config = container.resolve("config")

# Use an individual step directly
step = BinarizationStep(config=config.binarization_config)
result = step.run(input_image)
binary_image = result.to_array()
```

### Method Research
```python
from src.utils.binarization import BinarizationMethods

# Research different methods
methods = BinarizationMethods()
for method_name in methods.get_available_methods():
    result = methods.apply_method(method_name, image)
    analyze_result(result, method_name)
```

## 🚀 Performance Characteristics

### Binarization Methods (Processing Speed)
- **Fastest**: `global`, `otsu` (~0.01s per image)
- **Moderate**: `adaptive`, `morphological` (~0.05s per image)  
- **Slower**: `multi_otsu`, `line_enhanced`, `combined_differential` (~0.1s per image)

### Production Method Quality
- **Combined Differential**: Optimized for thick grid preservation
- **Grid Coverage**: ~15-25% typical (thick 21px lines)
- **Noise Removal**: Automatic spurious element filtering
- **Robustness**: Handles cellular content and lighting variations

## 🔮 Extensibility

### Adding New Binarization Methods
1. Add method to the `utils/binarization` package
2. Update `ThresholdMethod` enum
3. Add method info to discovery functions
4. Update documentation

### Adding New Pipeline Steps
1. Inherit from `PipelineStep` base class
2. Implement `run(ctx)` method
3. Add configuration schema
4. Add to main pipeline

### Custom Debug Outputs
1. Create custom drawer inheriting from `Drawer`
2. Implement the `draw(image, results, metadata)` method
3. Inject into the debugger: `Debugger(logger=..., debug_config=..., drawer=CustomDrawer())`
4. Call `debugger.save_debug_image(filename, image, results, metadata)`

---

## 📖 Related Documentation

- **[BINARIZATION_METHODS_GUIDE.md](BINARIZATION_METHODS_GUIDE.md)** - Complete binarization methods guide
- **[DEBUG_SYSTEM_GUIDE.md](DEBUG_SYSTEM_GUIDE.md)** - Debug visualization system
- **[LOGGING_CONFIGURATION.md](LOGGING_CONFIGURATION.md)** - Logging configuration

*This system is designed for both production efficiency and research flexibility.*
