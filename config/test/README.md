# Test Configuration Files

This folder contains configuration files specifically designed for testing individual pipeline steps in isolation.

## Purpose

These configurations are separate from the main pipeline configuration (`init_config.json`) and are optimized for:

- **Standalone Testing**: Each step can be tested independently
- **Debug Output**: Enhanced debugging and visualization settings
- **Isolated Parameters**: Step-specific configurations without pipeline overhead
- **Development**: Quick iteration during development and validation

## Files

### Current Test Configurations

- **`binarization.json`**: Configuration for testing binarization methods
  - Contains only: `general`, `binarization`, `log`, `debug` sections
  - Input filter: `_raw` suffix (processes raw grayscale images)
  - Output suffix: `_binarized` (generates binarized results)
  - No output path defined (testing focuses on debug visualization)
  - Debug and logging always enabled for analysis
  - Debug output directory: `debug_output/test_binarization`
  - Result file name: `results.csv`

- **`grid_detection.json`**: Configuration for testing grid detection algorithms
  - Contains only: `general`, `grid_detection`, `log`, `debug` sections
  - Input filter: `_binarized` suffix (processes pre-binarized images)
  - Output suffix: `_grid_detected` (generates detection results)
  - No output path defined (testing focuses on debug visualization)
  - Debug and logging always enabled for analysis
  - Debug output directory: `debug_output/test_grid_detection`
  - Result file name: `results.csv`
  - No binarization section - expects pre-binarized images

### Legacy Test Configurations

- **`test_grid_detection_config.json`**: Original grid detection test config (moved from config/)
- **`test_img_binarization.json`**: Original binarization test config (moved from config/)

## Testing Philosophy

Test configurations are designed for algorithm development and validation:

- **No output paths**: Testing focuses on debug visualization, not file output
- **Suffix filtering**: Process specific file types (e.g., `_raw` for grayscale, `_binarized` for binary)
- **Debug always enabled**: Essential for understanding algorithm behavior
- **Console logging**: Immediate feedback during testing
- **Focused sections**: Only include configuration relevant to the step being tested

## Typical Testing Workflow

```bash
# 1. Test binarization on raw grayscale images
python src/scripts/test_binarization.py config/test/binarization.json
# Input: image001_raw.png → Debug: debug_output/test_binarization/image001_raw_binarized.png
# Result suffix: _binarized

# 2. Test grid detection on pre-binarized images
python src/scripts/test_detection.py config/test/grid_detection.json
# Input: image001_binarized.png → Debug: debug_output/test_grid_detection/image001_binarized_grid_detected.png
# Result suffix: _grid_detected
```

This creates a clear pipeline: `raw` → `binarized` → `grid_detected`

## Adding New Test Configurations

When creating new test configurations:

1. **Follow naming convention**: `{step_name}_test_config.json`
2. **Include debug settings**: Enable visualization and set appropriate output directories
3. **Optimize for testing**: Focus on the specific step being tested
4. **Document parameters**: Add comments or maintain this README

## Structure

Test configurations should only include sections relevant to the step being tested:

**For Binarization Testing:**
```json
{
  "general": {
    "log": true,
    "debug": false
  },
  "binarization": {
    "threshold_method": "combined_differential"
  },
  "log": { ... },
  "debug": {
    "output_path": "debug_output/test_binarization",
    "save_results": false,
    "result_file_name": "results.csv"
  }
}
```

**For Grid Detection Testing:**
```json
{
  "general": {
    "log": true,
    "debug": true
  },
  "grid_detection": {
    "angle_deg": 2.0,
    // ... other grid detection parameters
  },
  "log": { ... },
  "debug": {
    "output_path": "debug_output/test_grid_detection",
    "save_results": true,
    "result_file_name": "results.csv"
  }
}
```

**Note:** Missing configuration sections will use default values from the configuration schema, allowing test configs to focus only on the step being tested.
