# SlidePrep System Overview

## 🧬 What is SlidePrep?

SlidePrep is a modular image processing pipeline designed to generate high-quality Whole Slide Images (WSI) from microscopy image tiles. It automatically detects and removes grid lines that appear during tile capture, then reconstructs the full slide using advanced stitching techniques.

## 🏗️ System Architecture

### Pipeline Stages

1. **Grayscale Conversion** - Standardize input images to grayscale
2. **Image Binarization** - Convert to binary using optimized thresholding ⭐
3. **Grid Line Detection** - Detect horizontal and vertical grid patterns  
4. **Grid Mask Generation** - Create masks for removing detected grid lines
5. **Grid Removal** - Apply masks to clean grid artifacts from images
6. **Whole Slide Stitching** - Reconstruct full slide from cleaned tiles (via Ashlar)

### Core Components

```
SlidePrep/
├── config/                 # Configuration schemas and settings
│   ├── config_schema.py   # Typed configuration classes
│   └── init_config.json   # Default configuration values
├── core/                   # Core pipeline infrastructure
│   ├── context.py         # Shared pipeline state management
│   ├── step.py            # Base classes for pipeline steps
│   ├── logger.py          # Logging system
│   └── debugger.py        # Debug visualization system
├── steps/                  # Individual processing steps
│   ├── binarization.py    # Binary conversion (59 lines, optimized)
│   └── grid_detection.py  # Grid pattern detection
├── utils/                  # Utility modules
│   ├── binarization/          # Thresholding methods package
│   ├── image_utils.py     # Image processing utilities
│   └── detection/         # Grid detection utilities
└── main.py                # Main pipeline entry point
```

## 🎯 Production vs Research

### Production Use (Simplified)
The system is optimized for production with sensible defaults:

```python
from steps.binarization import BinarizationStep
from config.config_schema import BinarizationConfig
import numpy as np

# Simple production usage
config = BinarizationConfig()  # Uses combined_differential by default
step = BinarizationStep(config)
result: np.ndarray = step.run(image_array)  # Returns binary image directly
```

**Key Features**:
- **Combined Differential method** (21px thick grids, ~2° rotation)
- **Spurious element removal** (filters out cellular content)
- **Optimized parameters** (production-tested)
- **Minimal configuration** required

### Research Use (Comprehensive)
Full access to all methods for experimentation:

```python
from utils.binarization import BinarizationMethods, ThresholdMethod

methods = BinarizationMethods()
# Access all 7 methods: global, otsu, adaptive, multi_otsu, 
# line_enhanced, morphological, combined_differential
binary = methods.apply_method(ThresholdMethod.MULTI_OTSU, image)
```

**Key Features**:
- **7 different methods** with full parameter control
- **Method comparison tools** (interactive demo)
- **Debug callbacks** and detailed information
- **Comprehensive documentation** with examples

## 🔧 API Design Principles

### Direct Array Processing
Pipeline steps use direct numpy array processing for optimal performance and clarity:

```python
# Each step processes arrays directly and returns results
binary_image: np.ndarray = binarization_step.run(grayscale_image)
detections, metadata = grid_detection_step.run(binary_image)
```

### Type Safety (PEP 484)
All functions include comprehensive type hints for IDE support and static analysis:

```python
def run(self, data: np.ndarray) -> np.ndarray:
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
@dataclass
class BinarizationConfig:
    threshold_method: str = "combined_differential"
    
    def __post_init__(self) -> None:
        """Validate binarization method selection."""
        # Comprehensive validation runs automatically
```

## ⚙️ Configuration System

### Typed Configuration
All components use typed configuration classes for safety and clarity:

```python
from config.config_schema import BinarizationConfig, GridDetectionConfig

# Type-safe configuration
binarization_config = BinarizationConfig(
    threshold_method="combined_differential",
    debug_enabled=True
)

grid_config = GridDetectionConfig(
    template_size=21,
    rotation_range=(-5, 5)
)
```

### Configuration Files
Default settings stored in JSON with schema validation:

```json
{
  "binarization": {
    "threshold_method": "combined_differential",
    "invert": false
  },
  "grid_detection": {
    "template_size": 21,
    "rotation_range": [-5, 5]
  }
}
```

## 🔧 Pipeline Architecture

The pipeline uses a **direct input-output function chaining** approach with **dependency injection**:

```python
from core.bootstrap import bootstrap
from steps.binarization import BinarizationStep
from steps.grid_detection import GridDetectionStep

# Initialize services once at startup
bootstrap(config_path)

# Create pipeline steps (services auto-injected via container)
steps = [
    BinarizationStep(config.binarization_config),
    GridDetectionStep(config.grid_detection_config)
]

# Process data through pipeline - simple function chaining
current_data = input_image
for step in steps:
    result = step.run(current_data)
    
    # Handle different return types
    if isinstance(result, tuple):
        current_data, metadata = result  # e.g., grid detection returns (image, stats)
    else:
        current_data = result  # e.g., binarization returns just the image
```

## 🐛 Debug and Visualization

### Debug System
Integrated debug output with automatic drawer integration:

```python
from core.bootstrap import bootstrap_application

container = bootstrap_application(config_path)
step = BinarizationStep(
    config=container.config.binarization_config,
    debugger=container.debugger,
    logger=container.logger
)

# Automatic debug output when enabled:
result = step.run(image)
# Debugger automatically detects registered drawers and creates visualizations
```

### Test Runner Integration
Simplified testing with automatic debug output:

```python
from scripts.module_test_runner import StepTestRunner

runner = StepTestRunner(config_path)
step = GridDetectionStep(
    config=runner.cfg.grid_detection_config,
    debugger=runner.debugger,
    logger=runner.logger
)

# Process entire directory with automatic debug visualization
runner.run_on_directory(step, "grid_detection")
```

### Logging System
Comprehensive logging for monitoring and debugging:

```python
from core.logger import Logger

logger = Logger(level="DEBUG", output_file="pipeline.log")
step = BinarizationStep(config, logger=logger)

# Logs processing time, parameters, and results
```

## 🧪 Testing and Validation

### Production Testing
Simple validation of the production method:

```bash
python scripts/test_binarization.py --input /path/to/images
```

### Interactive Exploration
Visual comparison of all binarization methods:

```bash
python demo_binarization_methods.py --image /path/to/image.png
```

### Grid Detection Testing
Validate grid detection separately:

```bash
python scripts/run_grid_detection.py \
  --input /path/to/tiles \
  --config config/test_grid_detection_config.json
```

## 🎮 Usage Patterns

### Basic Pipeline Usage
```python
from core.bootstrap import bootstrap, get_config
from steps.binarization import BinarizationStep
from steps.grid_detection import GridDetectionStep

# Initialize application services
bootstrap(config_path)
config = get_config()

# Create and run pipeline
steps = [
    BinarizationStep(config.binarization_config),
    GridDetectionStep(config.grid_detection_config)
]

# Process image through pipeline
current_data = input_image
for step in steps:
    current_data = step.run(current_data)
```

### Individual Step Usage
```python
from core.bootstrap import bootstrap
from steps.binarization import BinarizationStep
import numpy as np

# Initialize services first
bootstrap(config_path)

# Use individual steps (services auto-injected)
step = BinarizationStep(config.binarization_config)
result: np.ndarray = step.run(input_image)

# Result is returned directly as binary image array
```

### Method Research
```python
from utils.binarization import BinarizationMethods

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
3. Register with debugger: `Debugger.register_drawer("step_name", DrawerClass)`
4. Use automatic integration: `debugger.save_debug_image("step_name", filename, image, results)`

---

## 📖 Related Documentation

- **[BINARIZATION_METHODS_GUIDE.md](BINARIZATION_METHODS_GUIDE.md)** - Complete binarization methods guide
- **[DEBUG_SYSTEM_GUIDE.md](DEBUG_SYSTEM_GUIDE.md)** - Debug visualization system
- **[LOGGING_CONFIGURATION.md](LOGGING_CONFIGURATION.md)** - Logging configuration

*This system is designed for both production efficiency and research flexibility.*
