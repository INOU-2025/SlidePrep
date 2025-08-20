# 🧬 SlidePrep - Microscopy Image Processing Pipeline

A modular, production-ready image processing pipeline for generating high-quality Whole Slide Images (WSI) from microscopy image tiles. Automatically detects and removes grid lines that interfere with downstream stitching, then reconstructs the full slide.

**🎯 Optimized for thick grid detection (21px lines, ~2° rotation) with cellular content preservation.**

---

## 🚀 Quick Start

### Production Use (Recommended)
```bash
# Run the pipeline using a configuration file
python main.py config/production.json

# Edit the configuration to change paths or apply a suffix filter
python main.py path/to/custom_config.json
```

Processed images are written to the directory specified by
`general.output_path` (default: `output`). Filenames preserve their original
extensions and optionally include `general.output_suffix`.

---

## 🏗️ Pipeline Architecture

**Current Implementation:**
1. **Image Binarization** - Production-optimized Combined Differential method
2. **Grid Line Detection** - Template matching with thick grid optimization
3. **Grid Mask Generation** - Create precise masks for grid removal
4. **Mask-Based Inpainting** - Remove grid artifacts using configurable models
5. **Image Conversion** - Convert tiles to a chosen format and mode so they can be digested by Ashlar
6. **Whole Slide Stitching** - Reconstruct full slide using Ashlar

**Production vs Research:**
- **Production**: Uses optimized Combined Differential method automatically
- **Research**: Access to all 7 methods via utilities module

---

## 📁 Project Structure

```
SlidePrep/
├── config/                       # Configuration schemas and settings
│   ├── config_schema.py         # Typed configuration classes
│   ├── production.json          # Sample production configuration
│   └── development.json         # Sample development configuration
├── docs/                        # Comprehensive documentation
├── src/                         # Source code
│   ├── core/                    # Core pipeline infrastructure
│   │   ├── context.py           # Shared pipeline state
│   │   ├── step.py              # Base pipeline step classes
│   │   ├── logger.py            # Logging system
│   │   └── debugger.py          # Debug visualization
│   ├── steps/                   # Processing steps (clean & focused)
│   │   ├── img_conversion.py    # Image format/mode conversion
│   │   ├── binarization.py      # 59 lines - Production binarization
│   │   ├── grid_detection.py    # Grid pattern detection
│   │   └── stitching.py         # Whole slide assembly with Ashlar
│   ├── utils/                   # Utility modules
│   │   ├── binarization/        # Thresholding methods package
│   │   ├── image_utils.py       # Image processing utilities
│   │   └── detection/           # Grid detection utilities
│   └── scripts/                 # Testing and validation
│       ├── test_binarization.py # Production method testing
│       ├── test_detection.py    # Grid detection testing
│       ├── test_img_conversion.py # Format/mode conversion testing
│       └── test_stitching.py    # Ashlar stitching testing
├── demo_binarization_methods.py # Interactive method comparison ⭐
└── main.py                      # Production pipeline entry point
```

---

## 🔧 Installation

### Conda Environment (Recommended)
```bash
conda env create -f environment.yml
conda activate slideprep
```

### Alternative: Pip Installation
```bash
pip install -r requirements.txt
```

---

## 📊 Binarization Methods

### Production Method (Automatic)
- **Combined Differential** - Optimized for 21px thick grids with ~2° rotation

### Research Methods (7 Available)
- **Global Threshold** - Fixed threshold value
- **Otsu** - Automatic threshold selection  
- **Adaptive** - Local neighborhood thresholding
- **Multi-Otsu** - Multi-class thresholding
- **Line Enhanced** - Specialized grid line detection
- **Morphological** - Noise reduction with shape operations
- **Combined Differential** - Production method (also available for research)

---

## ⚡ Usage Examples

### Complete Pipeline
```bash
# Run with the sample production configuration
python main.py config/production.json

# Use a custom configuration file
python main.py path/to/config.json
```

### In-memory Processing
```python
import cv2
from src.core.pipeline_service import PipelineService
from src.core.app_config_manager import AppConfigManager

gray = cv2.imread("tile.png", cv2.IMREAD_GRAYSCALE)

# Load from a configuration path
service = PipelineService(
    config_path="config/production.json",
    image_shape=(gray.shape[1], gray.shape[0]),
)

# Or provide a pre-loaded configuration object
cfg = AppConfigManager("config/production.json")
service = PipelineService(config=cfg, image_shape=(gray.shape[1], gray.shape[0]))

result = service.run(gray)
```

### Individual Step Testing
```bash
# Test image conversion
python src/scripts/test_img_conversion.py config/test/img_conversion.json

# Test binarization on sample images
python src/scripts/test_binarization.py config/test/binarization.json

# Test grid detection with visualization
python src/scripts/test_detection.py config/test/grid_detection.json

# Run grid refinement on serialized detection output
# (set `test.input_type` to "data" in your config)
python main.py config/development.json

# Test mask-based inpainting
python src/scripts/test_inpainting.py config/test/inpainting.json

# Generate a stitched OME-TIFF from processed tiles
python src/scripts/test_stitching.py config/test/stitching.json
```

---

## ⚙️ Configuration & Customization

### Production Configuration (Simple)
```python
from src.steps import BinarizationStep
from config.config_schema import BinarizationConfig

# Uses optimized defaults automatically
config = BinarizationConfig()  # Combined Differential method
step = BinarizationStep(config)
```

### Research Configuration (Full Control)
```python
from src.utils.binarization import BinarizationMethods, ThresholdMethod

methods = BinarizationMethods()

# Use any of the 7 available methods
binary = methods.apply_method(ThresholdMethod.ADAPTIVE, image, 
                             block_size=15, c_constant=5)
binary = methods.apply_method(ThresholdMethod.MULTI_OTSU, image, classes=3)
```

### Configuration Files
All parameters can be customized via JSON configuration:
```json
{
  "binarization": {
    "threshold_method": "combined_differential"
  },
  "grid_detection": {
    "template_size": 21,
    "rotation_range": [-5, 5]
  }
}
```

---

## 📚 Documentation

Comprehensive documentation is available in the [`docs/`](docs/) folder:

- **[docs/README.md](docs/README.md)** - Documentation index and quick start
- **[docs/BINARIZATION_METHODS_GUIDE.md](docs/BINARIZATION_METHODS_GUIDE.md)** - Complete binarization guide ⭐
- **[docs/SYSTEM_OVERVIEW.md](docs/SYSTEM_OVERVIEW.md)** - System architecture and development  
- **[docs/DEBUG_SYSTEM_GUIDE.md](docs/DEBUG_SYSTEM_GUIDE.md)** - Debug visualization system
- **[docs/LOGGING_CONFIGURATION.md](docs/LOGGING_CONFIGURATION.md)** - Logging setup

---

## 📄 License & Credits

**Developed by**: Ivan Rodriguez-Conde  
**Institution**: @SI6 @ESEI @Universidade de Vigo  
**Contact**: [ivarodriguez@uvigo.gal](mailto:ivarodriguez@uvigo.gal)
