# SlidePrep Documentation

Welcome to the SlidePrep documentation. This folder contains essential guides for using and understanding the SlidePrep microscopy image processing pipeline.

## 📚 Documentation Index

### Core Guides
- **[`SYSTEM_OVERVIEW.md`](SYSTEM_OVERVIEW.md)** - System architecture and development guide
- **[`CONFIGURATION_GUIDE.md`](CONFIGURATION_GUIDE.md)** - Complete configuration reference
- **[`BINARIZATION_METHODS_GUIDE.md`](BINARIZATION_METHODS_GUIDE.md)** - Binarization methods and optimization
- **[`DEBUG_SYSTEM_GUIDE.md`](DEBUG_SYSTEM_GUIDE.md)** - Debug visualization system
- **[`LOGGING_CONFIGURATION.md`](LOGGING_CONFIGURATION.md)** - Logging setup and configuration

## 🚀 Quick Start

### For Production Use
The system uses the **Combined Differential** method by default - just use `BinarizationConfig()`:

```python
from src.steps import BinarizationStep
from config.config_schema import BinarizationConfig
import numpy as np

config = BinarizationConfig()  # Uses combined_differential by default
step = BinarizationStep(config)
result: np.ndarray = step.run(image_array)  # Returns binary image directly
```

### Image Conversion
Convert images to a specific format and color mode:

```python
from src.steps import ImgConversionStep
from config.config_schema import ImgConversionConfig

cfg = ImgConversionConfig(format="jpeg", mode="RGB")
step = ImgConversionStep(cfg)
converted, metadata = step.run(image_array)
```

### For Research and Experimentation
Use the binarization utilities for access to all 7 methods:

```python
from src.utils.binarization import BinarizationMethods, ThresholdMethod

methods = BinarizationMethods()
binary = methods.apply_method(ThresholdMethod.MULTI_OTSU, image)
```

### Interactive Demo
Compare all methods visually:

```bash
python demo_binarization_methods.py --image your_image.png
```

## 📖 What Each Document Covers

### BINARIZATION_METHODS_GUIDE.md
- **All 7 binarization methods** with working code examples
- **Parameter explanations** and best practices
- **Method selection guidelines** 

### SYSTEM_OVERVIEW.md
- **Complete architecture overview** with typed components
- **Pipeline design patterns** and step interfaces
- **Production vs research usage** with clear API examples

### CONFIGURATION_GUIDE.md
- **Full configuration reference** with type validation
- **JSON schema documentation** and validation rules
- **Environment-specific settings** for different deployments

### DEBUG_SYSTEM_GUIDE.md
- **Visualization system** for development and debugging
- **Debug output management** and analysis tools

## 📝 Code Quality Standards

### Type Hints (PEP 484)
All functions include comprehensive type annotations for better IDE support and static analysis:

```python
def run(self, data: np.ndarray) -> np.ndarray:
    """Convert grayscale image to binary using configured method."""
```

### Documentation (PEP 257)
Professional docstrings explain behavior and purpose rather than implementation:

```python
class BinarizationStep(PipelineStep):
    """Pipeline step for converting grayscale images to binary using thresholding methods.
    
    Applies configurable binarization algorithms to separate foreground from background,
    with automatic grayscale conversion for color inputs.
    """
```

### API Design
- **Direct array processing**: Functions return results directly, not through context objects
- **Clear type contracts**: Every function signature includes input/output types
- **Comprehensive validation**: Configuration classes validate parameters automatically
- **Behavioral documentation**: Docstrings explain what functions do and why, not how 
- **Troubleshooting** common issues
- **Integration examples** for production and research

### SYSTEM_OVERVIEW.md  
- **Pipeline architecture** and component overview
- **Configuration system** and how components interact
- **Development guidelines** for extending the system

### CONFIGURATION_GUIDE.md
- **Complete configuration reference** with all settings explained
- **Validation and error handling** guide
- **Best practices** for production and development
- **Troubleshooting** common configuration issues
### DEBUG_SYSTEM_GUIDE.md
- **Debug visualization** system for development and grid detection
- **Integration with new result/metadata structure** (no legacy objects)
- **Drawer configuration** and usage, with all parameters sourced from JSON config
- **Creating custom debug outputs** for new pipeline steps

### LOGGING_CONFIGURATION.md
- **Logging setup** and configuration
- **Log levels** and output formats
- **Integration** with the pipeline system

## 📁 Project Structure

```
SlidePrep/
├── config/          # Configuration schemas and files
├── docs/           # This documentation folder
├── src/            # Source code
│   ├── core/       # Core pipeline interfaces and utilities
│   ├── steps/      # Individual processing steps
│   ├── utils/      # Utility modules (binarization, image processing, etc.)
│   └── scripts/    # Testing and validation scripts
```

## 🆘 Getting Help

1. **For binarization questions**: Start with [`BINARIZATION_METHODS_GUIDE.md`](BINARIZATION_METHODS_GUIDE.md)
2. **For system architecture**: See [`SYSTEM_OVERVIEW.md`](SYSTEM_OVERVIEW.md)  
3. **For debugging issues**: Check [`DEBUG_SYSTEM_GUIDE.md`](DEBUG_SYSTEM_GUIDE.md)

