# Configuration Files Overview

## 📁 Configuration Structure

```
config/
├── production.json        # Production-optimized settings
├── development.json       # Development-friendly settings
└── test/
    ├── binarization.json     # Binarization testing
    └── grid_detection.json   # Grid detection testing
```

## 🎯 Configuration Selection Guide

### **When to use each configuration:**

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

#### Using Serialized Intermediate Results
- **Purpose:** Test grid refinement directly from saved detection results
- **Configuration:** Set `debug.input_result_file_name` to a JSON file produced by the detection step
- **Effect:** Pipeline bypasses image loading and runs only the refinement step

## 🚀 Quick Usage

```bash
# Production usage
python main.py --config config/production.json

# Development usage
python main.py --config config/development.json

# Test specific components
python src/scripts/test_binarization.py config/test/binarization.json
python src/scripts/test_detection.py config/test/grid_detection.json
```

## 🔧 Key Differences

| Config | Debug | Log Level | Log Output | Save Composite | Debug Dir |
|--------|-------|-----------|------------|----------------|-----------|
| production | ❌ | WARNING | File only | ❌ | debug |
| development | ✅ | DEBUG | File + Console | ✅ | debug/development |
| test/* | Varies | INFO | Console | ❌ | debug/test_* |

This structure provides clear separation of concerns and makes it easy to choose the right configuration for any use case.
