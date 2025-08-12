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
  - Contains: `general`, `binarization`, `log`, `debug`, `test` sections
  - Input filter: `_raw` suffix (processes raw grayscale images)
  - Output suffix: `_binarized`
  - Debug and logging always enabled for analysis
  - Debug artifacts stored under `<test.output_path>/debug`

- **`grid_detection.json`**: Configuration for testing grid detection algorithms
  - Contains: `general`, `grid_detection`, `log`, `debug`, `test` sections
  - Input filter: `_binarized` suffix (processes pre-binarized images)
  - Output suffix: `_grid_detected`
  - Debug and logging always enabled for analysis
  - Debug artifacts stored under `<test.output_path>/debug`
  - No binarization section - expects pre-binarized images

### Legacy Test Configurations

- **`test_grid_detection_config.json`**: Original grid detection test config (moved from config/)
- **`test_img_binarization.json`**: Original binarization test config (moved from config/)

## Testing Philosophy

Test configurations are designed for algorithm development and validation:

- **Explicit test paths**: `test.input_path` and `test.output_path` isolate test data and results
- **Suffix filtering**: Process specific file types (e.g., `_raw` for grayscale, `_binarized` for binary)
- **Debug always enabled**: Essential for understanding algorithm behavior
- **Console logging**: Immediate feedback during testing
- **Focused sections**: Only include configuration relevant to the step being tested

## Typical Testing Workflow

```bash
# 1. Test binarization on raw grayscale images
python src/scripts/test_binarization.py config/test/binarization.json
# Input: image001_raw.png → Debug: <test.output_path>/debug/image001_raw_binarized.png
# Result suffix: _binarized

# 2. Test grid detection on pre-binarized images
python src/scripts/test_detection.py config/test/grid_detection.json
# Input: image001_binarized.png → Debug: <test.output_path>/debug/image001_binarized_grid_detected.png
# Result suffix: _grid_detected
```

This creates a clear pipeline: `raw` → `binarized` → `grid_detected`

## Adding New Test Configurations

When creating new test configurations:

1. **Follow naming convention**: `{step_name}_test_config.json`
2. **Include test paths**: Add a `test` section with `input_path` and `output_path`
3. **Include debug settings**: Enable visualization and set relative directories
4. **Optimize for testing**: Focus on the specific step being tested
5. **Document parameters**: Add comments or maintain this README

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
  "log": {
    "relative_path": "log"      // Optional
  },
  "debug": {
    "relative_path": "debug",   // Optional
    "saved_artifact_type": "image",
    "save_composite_img": false,
    "save_aggregated_data": false
  },
  "test": {
    "input_path": "/path/to/test/images",
    "output_path": "/path/to/test/output",
    "input_type": "image"
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
    "angle_deg": 2.0
    // ... other grid detection parameters
  },
  "log": {
    "relative_path": "log"      // Optional
  },
  "debug": {
    "relative_path": "debug",   // Optional
    "saved_artifact_type": "both",
    "save_composite_img": false,
    "save_aggregated_data": true
  },
  "test": {
    "input_path": "/path/to/test/images",
    "output_path": "/path/to/test/output",
    "input_type": "image"
  }
}
```

**Note:** Missing configuration sections will use default values from the configuration schema, allowing test configs to focus only on the step being tested.
