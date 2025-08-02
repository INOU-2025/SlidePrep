# SlidePrep Documentation

Welcome to the SlidePrep documentation. This folder contains essential guides for using and understanding the SlidePrep microscopy image processing pipeline.

## � Documentation Index

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
from steps.binarization import BinarizationStep
from config.config_schema import BinarizationConfig

config = BinarizationConfig()  # Uses combined_differential by default
step = BinarizationStep(config)
step.run(ctx)  # ctx.binarized_image contains the result
```

### For Research and Experimentation
Use the binarization utilities for access to all 7 methods:

```python
from utils.binarization_methods import BinarizationMethods, ThresholdMethod

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
- **Debug visualization** system for development
- **Creating custom debug outputs** for new steps
- **Drawer configuration** and usage

### LOGGING_CONFIGURATION.md
- **Logging setup** and configuration
- **Log levels** and output formats
- **Integration** with the pipeline system

## 📁 Project Structure

```
SlidePrep/
├── config/          # Configuration schemas and files
├── core/           # Core pipeline interfaces and utilities  
├── steps/          # Individual processing steps
├── utils/          # Utility modules (binarization, image processing, etc.)
├── scripts/        # Testing and validation scripts
├── docs/           # This documentation folder
└── demo_binarization_methods.py  # Interactive method comparison
```

## 🆘 Getting Help

1. **For binarization questions**: Start with [`BINARIZATION_METHODS_GUIDE.md`](BINARIZATION_METHODS_GUIDE.md)
2. **For system architecture**: See [`SYSTEM_OVERVIEW.md`](SYSTEM_OVERVIEW.md)  
3. **For debugging issues**: Check [`DEBUG_SYSTEM_GUIDE.md`](DEBUG_SYSTEM_GUIDE.md)
4. **For interactive exploration**: Run `python demo_binarization_methods.py`

---

*Last updated: July 31, 2025*
