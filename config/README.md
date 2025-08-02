# Configuration Files Overview

## 📁 Configuration Structure

```
config/
├── default.json           # Main default configuration
├── production.json        # Production-optimized settings
├── development.json       # Development-friendly settings
└── test/
    ├── binarization.json     # Binarization testing
    └── grid_detection.json   # Grid detection testing
```

## 🎯 Configuration Selection Guide

### **When to use each configuration:**

#### `default.json`
- **Purpose:** General-purpose configuration
- **Debug:** Enabled (for visibility)
- **Logging:** INFO level, file + console
- **Use for:** General testing and development

#### `production.json`
- **Purpose:** Production deployments
- **Debug:** Disabled (performance)
- **Logging:** WARNING level, file only
- **Use for:** Production environments, batch processing

#### `development.json`
- **Purpose:** Active development work
- **Debug:** Enabled with composite saves
- **Logging:** DEBUG level, file + console
- **Use for:** Debugging, algorithm development, research

#### `test/binarization.json`
- **Purpose:** Isolated binarization testing
- **Contents:** Only general, binarization, log, debug sections
- **Input filter:** `_raw` suffix (for grayscale images)
- **Output:** No output path (debug visualization only)
- **Use for:** Testing binarization methods on raw grayscale images

#### `test/grid_detection.json`
- **Purpose:** Isolated grid detection testing
- **Contents:** Only general, grid_detection, log, debug sections
- **Input filter:** `_binarized` suffix (for pre-binarized images)
- **Output:** No output path (debug visualization only)
- **Note:** No binarization config - expects pre-binarized images
- **Use for:** Testing grid detection algorithms on binarized inputs

## 🚀 Quick Usage

```bash
# Default usage (uses default.json internally)
python main.py --input /path/to/images

# Production usage
python main.py --config config/production.json

# Development usage
python main.py --config config/development.json

# Test specific components
python scripts/test_binarization.py config/test/binarization.json
python scripts/test_grid_detection.py config/test/grid_detection.json
```

## 🔧 Key Differences

| Config | Debug | Log Level | Log Output | Save Composite | Debug Dir |
|--------|-------|-----------|------------|----------------|-----------|
| default | ✅ | INFO | File + Console | ❌ | debug_output |
| production | ❌ | WARNING | File only | ❌ | debug_output |
| development | ✅ | DEBUG | File + Console | ✅ | debug_output/development |
| test/* | Varies | INFO | Console | ❌ | debug_output/test_* |

This structure provides clear separation of concerns and makes it easy to choose the right configuration for any use case.
