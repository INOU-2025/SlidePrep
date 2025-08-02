# 🧬 SlidePrep - Microscopy Image Processing Pipeline

A modular, production-ready image processing pipeline for generating high-quality Whole Slide Images (WSI) from microscopy image tiles. Automatically detects and removes grid lines that interfere with downstream stitching, then reconstructs the full slide.

**🎯 Optimized for thick grid detection (21px lines, ~2° rotation) with cellular content preservation.**

---

## 🚀 Quick Start

### Production Use (Recommended)
```bash
# Process a directory of images with optimized defaults
python main.py --input /path/to/your/tiles

# Filter specific files (e.g., only process files ending with '_ch00')
python main.py --input /path/to/tiles --suffix "_ch00"
```

---

## 🏗️ Pipeline Architecture

**Current Implementation:**
1. **Image Binarization** - Production-optimized Combined Differential method
2. **Grid Line Detection** - Template matching with thick grid optimization
3. **Grid Mask Generation** - Create precise masks for grid removal *(planned)*
4. **Grid Removal from Tiles** - Clean grid artifacts from images *(planned)*
5. **Whole Slide Stitching** - Reconstruct full slide using Ashlar *(planned)*

**Production vs Research:**
- **Production**: Uses optimized Combined Differential method automatically
- **Research**: Access to all 7 methods via utilities module

---

## 📁 Project Structure

```
SlidePrep/
├── config/                       # Configuration schemas and settings
│   ├── config_schema.py         # Typed configuration classes
│   └── init_config.json         # Default production settings
├── core/                        # Core pipeline infrastructure  
│   ├── context.py              # Shared pipeline state
│   ├── step.py                 # Base pipeline step classes
│   ├── logger.py               # Logging system
│   └── debugger.py             # Debug visualization
├── steps/                       # Processing steps (clean & focused)
│   ├── binarization.py         # 59 lines - Production binarization
│   └── grid_detection.py       # Grid pattern detection
├── utils/                       # Utility modules
│   ├── binarization/          # Thresholding methods package
│   ├── image_utils.py          # Image processing utilities
│   └── detection/              # Grid detection utilities
├── scripts/                     # Testing and validation
│   ├── test_binarization.py    # Production method testing
│   └── run_grid_detection.py   # Grid detection testing
├── docs/                        # Comprehensive documentation
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
# Process all images in a directory
python main.py --input /path/to/microscopy/tiles

# Process only specific files (e.g., channel 0)
python main.py --input /path/to/tiles --suffix "_ch00"

# Use custom configuration
python main.py --input /path/to/tiles --config my_config.json
```

### Individual Step Testing
```bash
# Test binarization on sample images
python scripts/test_binarization.py --input /path/to/images

# Test grid detection with visualization  
python scripts/run_grid_detection.py \
  --input /path/to/tiles \
  --config config/test_grid_detection_config.json
```

---

## ⚙️ Configuration & Customization

### Production Configuration (Simple)
```python
from steps.binarization import BinarizationStep
from config.config_schema import BinarizationConfig

# Uses optimized defaults automatically
config = BinarizationConfig()  # Combined Differential method
step = BinarizationStep(config)
```

### Research Configuration (Full Control)
```python
from utils.binarization import BinarizationMethods, ThresholdMethod

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
