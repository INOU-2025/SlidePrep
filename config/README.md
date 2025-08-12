# Configuration Files Overview

## 📁 Configuration Structure

```
config/
├── production.json        # Production-optimized settings
├── development.json       # Development-friendly settings
└── test/
    ├── binarization.json       # Binarization testing
    ├── grid_detection.json     # Grid detection testing
    ├── grid_refinement.json    # Grid refinement testing
    ├── mask_creation.json      # Mask generation testing
    └── inpainting.json         # Inpainting testing
```

Test configuration files include a dedicated `test` section that defines
where test images are read from and where results are written. The `log`
and `debug` sections specify optional directories relative to the test
run's `output_path`.

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
- **Output:** Defined via `test.output_path`
- **Use for:** Testing binarization methods on raw grayscale images
- **Debug artifacts:** stored under `<output_path>/debug`

#### `test/grid_detection.json`
- **Purpose:** Isolated grid detection testing
- **Contents:** Only general, grid_detection, log, debug sections
- **Input filter:** `_binarized` suffix (for pre-binarized images)
- **Output:** Defined via `test.output_path`
- **Note:** No binarization config - expects pre-binarized images
- **Use for:** Testing grid detection algorithms on binarized inputs
- **Debug artifacts:** stored under `<output_path>/debug`

#### `test/mask_creation.json`
- **Purpose:** Isolated mask generation testing
- **Contents:** general, log and debug sections; reads refined detection results
- **Output:** Defined via `test.output_path`
- **Use for:** Convert refined detection contours into binary masks
- **Debug artifacts:** stored under `<output_path>/debug`

#### `test/inpainting.json`
- **Purpose:** Mask-based inpainting testing
- **Contents:** general, inpainting, log and debug sections
- **Output:** Defined via `test.output_path`
- **Use for:** Remove grid artifacts using LaMa inpainting
- **Debug artifacts:** stored under `<output_path>/debug`

#### Using Serialized Intermediate Results
- **Purpose:** Test grid refinement directly from saved detection results
- **Configuration:** Set `test.input_type` to `"data"` so the step consumes serialized results instead of images
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
