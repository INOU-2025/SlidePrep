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
│   ├── binarization_methods.py  # All 7 binarization methods (400+ lines)
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

# Simple production usage
config = BinarizationConfig()  # Uses combined_differential by default
step = BinarizationStep(config)
step.run(ctx)  # Optimal results automatically
```

**Key Features**:
- **Combined Differential method** (21px thick grids, ~2° rotation)
- **Spurious element removal** (filters out cellular content)
- **Optimized parameters** (production-tested)
- **Minimal configuration** required

### Research Use (Comprehensive)
Full access to all methods for experimentation:

```python
from utils.binarization_methods import BinarizationMethods, ThresholdMethod

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

## 🔧 Pipeline Context

The `PipelineContext` manages shared state between processing steps:

```python
from core.context import PipelineContext

ctx = PipelineContext(image_path="input.png")

# Steps automatically populate context
ctx.gray_image       # ← Populated by grayscale conversion
ctx.binarized_image  # ← Populated by binarization step  
ctx.grid_mask        # ← Populated by grid detection
ctx.cleaned_image    # ← Populated by grid removal

# Each step can access previous results and add new ones
```

## 🐛 Debug and Visualization

### Debug System
Integrated debug output for development and troubleshooting:

```python
from core.debugger import Debugger

debugger = Debugger(output_folder="debug_output", enabled=True)
step = BinarizationStep(config, debugger=debugger)

# Automatically saves intermediate results:
# - Original input image
# - Binarization result
# - Any morphological operations
# - Final processed output
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
from main import SlidePrep
from config.config_schema import PipelineConfig

# Complete pipeline
config = PipelineConfig()
pipeline = SlidePrep(config)
results = pipeline.process_directory("/path/to/tiles")
```

### Individual Step Usage
```python
from steps.binarization import BinarizationStep
from core.context import PipelineContext

# Use individual steps
ctx = PipelineContext(image_path="test.png")
binarization_step = BinarizationStep(config)
binarization_step.run(ctx)

# Result available in ctx.binarized_image
```

### Method Research
```python
from utils.binarization_methods import BinarizationMethods

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
1. Add method to `utils.binarization_methods.py`
2. Update `ThresholdMethod` enum
3. Add method info to discovery functions
4. Update documentation

### Adding New Pipeline Steps
1. Inherit from `PipelineStep` base class
2. Implement `run(ctx)` method
3. Add configuration schema
4. Add to main pipeline

### Custom Debug Outputs
1. Create custom drawer in `utils.debug.drawers.py`
2. Register with debugger system
3. Use in your pipeline step

---

## 📖 Related Documentation

- **[BINARIZATION_METHODS_GUIDE.md](BINARIZATION_METHODS_GUIDE.md)** - Complete binarization methods guide
- **[DEBUG_SYSTEM_GUIDE.md](DEBUG_SYSTEM_GUIDE.md)** - Debug visualization system
- **[LOGGING_CONFIGURATION.md](LOGGING_CONFIGURATION.md)** - Logging configuration

*This system is designed for both production efficiency and research flexibility.*
