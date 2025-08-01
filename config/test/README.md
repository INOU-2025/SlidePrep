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

- **`binarization_test_config.json`**: Configuration for testing binarization methods
  - Contains only: `binarization`, `logging`, `debug` sections
  - Optimized debug output directory: `debug_output/test_binarization`
  - Production binarization method: `combined_differential`

- **`grid_detection_test_config.json`**: Configuration for testing grid detection algorithms
  - Contains only: `grid_detection`, `logging`, `debug` sections
  - Optimized debug output directory: `debug_output/test_grid_detection`
  - Tuned parameters for line detection and grid analysis

### Legacy Test Configurations

- **`test_grid_detection_config.json`**: Original grid detection test config (moved from config/)
- **`test_img_binarization.json`**: Original binarization test config (moved from config/)

## Usage

Test scripts automatically use these configurations:

```bash
# Binarization testing (uses binarization_test_config.json by default)
python scripts/test_binarization.py --input /path/to/images

# Grid detection testing (uses grid_detection_test_config.json by default)
python scripts/test_grid_detection.py --input /path/to/images

# Or specify a custom test config
python scripts/test_binarization.py --input /path/to/images --config config/test/custom_config.json
```

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
    "output_dir": "debug_output/test_binarization"
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
    "output_dir": "debug_output/test_grid_detection"
  }
}
```

**Note:** Missing configuration sections will use default values from the configuration schema, allowing test configs to focus only on the step being tested.
