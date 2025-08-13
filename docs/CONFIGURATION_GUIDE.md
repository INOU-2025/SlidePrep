# Configuration Guide

## 📋 Overview

SlidePrep uses a modular JSON-based configuration system with typed dataclasses for validation and IDE support. This guide covers all configuration options and best practices.

## 🏗️ Configuration Structure

The configuration is organized into logical sections:

```json
{
  "general": {      // Global settings for all operations
    // Input/output paths and filters
  },
  "binarization": { // Image binarization settings
    // Threshold methods and parameters
  },
  "grid_detection": { // Grid pattern detection settings
    // Template matching and analysis parameters
  },
  "stitching": {    // Whole slide stitching settings
    // Ashlar configuration for final assembly
  },
  "log": {         // Logging configuration
    // File/console output and levels
  },
  "debug": {       // Debug visualization settings
    // Output directories and options
  },
  "test": {        // Optional test overrides
    // Input/output paths and types for isolated runs
  }
}
```

## ⚙️ Configuration Sections

### General Configuration

Controls global behavior across all pipeline steps:

```json
{
  "general": {
    "input_path": "path/to/input/images",      // Required: Input directory
    "output_path": "output",                   // Output directory (default: "output")
    "suffix_filter": "_ch00",                  // Filter files by suffix (optional)
    "output_suffix": "_processed",             // Add suffix to output files (optional)
    "log": true,                              // Enable logging (default: true)
    "debug": false                            // Enable debug visualization (default: false)
  }
}
```

**Validation:**
- `input_path` must exist if specified
- All boolean values default to appropriate settings

### Test Configuration

Provides isolated paths for test runs without altering general configuration:

```json
{
  "test": {
    "input_path": "/path/to/test/images",
    "output_path": "/path/to/test/output",
    "input_type": "image",           // "image" or "data"
    "max_images": 10                  // Optional limit on processed files
  }
}
```

If provided, these paths are used exclusively by test runners and do not
modify the values in the `general` section. The `input_type` field selects
whether the step operates on image files or serialized data. When
`input_type` is set to `"data"`, test runners locate the corresponding
source images in `general.input_path` while reading JSON files from
`test.input_path`.

The optional `max_images` field limits how many files are processed during
test runs. When omitted, all matching files are processed.

### Image Conversion Configuration

Controls output format and color mode of processed images:

```json
{
  "img_conversion": {
    "format": "png",   // "jpeg", "png" or "tiff"
    "mode": "RGB"      // "RGB" or "grayscale"
  }
}
```

- `format`: Desired file format for the converted image.
- `mode`: Output color mode. Use `"RGB"` for color or `"grayscale"` for
  single-channel images.

### Binarization Configuration

Controls image binarization behavior:

```json
{
  "binarization": {
    "threshold_method": "combined_differential"  // Binarization algorithm
  }
}
```

**Valid threshold methods:**
- `"otsu"`: Otsu's automatic threshold selection
- `"triangle"`: Triangle algorithm for bimodal images
- `"li"`: Li's minimum cross entropy
- `"yen"`: Yen's maximum correlation criterion
- `"isodata"`: Iterative isodata algorithm
- `"minimum"`: Minimum error thresholding
- `"combined_differential"`: **Recommended** - Optimized for thick grids
- `"adaptive_gaussian"`: Gaussian-weighted adaptive threshold
- `"adaptive_mean"`: Mean-weighted adaptive threshold

### Grid Detection Configuration

Controls grid pattern detection and analysis:

```json
{
  "grid_detection": {
    "angle_deg": 2.0,                    // Expected grid rotation (0-45°) - REQUIRED
    "margin": 5,                         // Border margin for touch detection - REQUIRED
    "percentile_thresh": 2,              // Template matching percentile (1-100) - REQUIRED
    "horizontal_area_threshold": 2000,   // Min area for horizontal lines - REQUIRED
    "vertical_area_threshold": 2000,     // Min area for vertical lines - REQUIRED
    "line_length": 40,                   // Template line length - REQUIRED
    "line_thickness": 21,                // Expected grid line thickness - REQUIRED
    "length_threshold_factor": 0.55      // Length threshold factor (0-1) - REQUIRED
  }
}
```

**All parameters are required** - no defaults are provided to ensure explicit configuration for your specific grid patterns.

**Parameter Guidelines:**
- `angle_deg`: Expected rotation of grid lines (most grids: 0-5°)
- `percentile_thresh`: Lower values = more sensitive detection
- `line_thickness`: Match your actual grid thickness for best results
- `length_threshold_factor`: Higher values = stricter length requirements

### Inpainting Configuration

Controls mask-based grid removal using configurable models:

```json
{
  "inpainting": {
    "model": "lama",          // Inpainting algorithm (currently only "lama")
    "mask_path": "path/to/masks", // Directory containing binary mask images
    "mask_suffix": "_mask"     // Suffix used to locate mask files
  }
}
```

**Parameters:**
- `model`: Inpainting algorithm identifier. `"lama"` uses Samsung's LaMa model.
- `mask_path`: Directory containing mask images generated by the previous step.
- `mask_suffix`: Suffix appended to each filename when searching for its mask.

### Stitching Configuration

Controls whole slide assembly using Ashlar:

```json
{
  "stitching": {
    "output_filename": "stitched_slide.ome.tif", // Output OME-TIFF name
    "tile_glob": "*.tif"                        // Glob to locate tiles
  }
}
```

- `output_filename`: Name of the generated OME-TIFF. If a relative path is
  provided, it is written inside the pipeline's output directory.
- `tile_glob`: Glob pattern used to collect processed tile images for stitching.

### Logging Configuration

Controls logging output and verbosity:

```json
{
  "log": {
    "log_to_file": true,                // Enable file logging
    "log_to_console": false,            // Enable console logging
    "log_file_name": "app.log",         // Log filename
    "log_level": "INFO",                // Logging level
    "relative_path": "log"             // Optional directory inside output path
  }
}
```

**Valid log levels:**
- `"DEBUG"`: Detailed diagnostic information
- `"INFO"`: **Recommended** - General information
- `"WARNING"`: Warning messages only
- `"ERROR"`: Error messages only
- `"CRITICAL"`: Critical errors only

### Debug Configuration

Controls debug visualization and output:

```json
{
  "debug": {
    "relative_path": "debug",                  // Optional directory inside output path
    "saved_artifact_type": "image",            // "image" | "data" | "both"
    "save_composite_img": false,                // Save side-by-side comparisons
    "save_aggregated_data": true,               // Enable aggregated result saving
    "input_result_file_name": "results.json"   // Filename for serialized intermediate results
  }
}
```

**Debug Options:**
- Debug enablement is controlled by `general.debug` (single source of truth)
- `saved_artifact_type`: Determines whether images, data, or both are saved
- `save_composite_img`: Creates before/after comparison images
- `input_result_file_name`: JSON file containing intermediate step outputs.
  Used when `test.input_type` is set to `"data"` to locate serialized results.
- `save_aggregated_data`: Persist step outputs to `aggregated_data.json`

## 📁 Configuration Files

### Main Configurations

**File:** `config/production.json`
- **Purpose:** Production-optimized configuration
- **Usage:** `python main.py config/production.json`
- **Settings:** Optimized for production (debug=false, minimal logging, WARNING level)

**File:** `config/development.json`
- **Purpose:** Development-friendly configuration
- **Usage:** `python main.py config/development.json`
- **Settings:** Developer-friendly (debug=true, verbose logging, DEBUG level, composite saves)

### Test Configurations

**Directory:** `config/test/`

**Grid Detection Testing:**
```bash
python src/scripts/test_detection.py config/test/grid_detection.json
```

**Binarization Testing:**
```bash
python src/scripts/test_binarization.py config/test/binarization.json
```

## 🔧 Usage Patterns

### Command Line Usage

```bash
# Run with the sample production configuration
python main.py config/production.json

# Run with the development configuration
python main.py config/development.json

# Use a custom configuration file
python main.py path/to/custom_config.json
```

### Programmatic Usage

```python
from src.core.bootstrap import bootstrap, get_config

# Bootstrap with different configurations
bootstrap("config/production.json")   # Production optimized
bootstrap("config/development.json")  # Development friendly

config = get_config()

# Access typed configuration
input_path = config.general_config.input_path
threshold_method = config.binarization_config.threshold_method
debug_enabled = config.debug_active  # Smart debug detection
```

## ✅ Validation and Error Handling

The configuration system includes comprehensive validation:

### Automatic Validation

- **File paths:** Validates that input paths exist
- **Numeric ranges:** Ensures parameters are within valid ranges
- **Enum values:** Validates threshold methods and log levels
- **Type checking:** Enforces correct data types

### Error Messages

```python
# Invalid threshold method
ValueError: Invalid threshold method: invalid_method. 
Valid methods: adaptive_gaussian, adaptive_mean, combined_differential, ...

# Invalid parameter range
ValueError: angle_deg must be between 0 and 45, got: 50.0

# Missing input path
ValueError: Input path does not exist: /nonexistent/path
```

## 💡 Best Practices

### Configuration Organization

1. **Use test configs for development:** Keep test configurations separate
2. **Document custom settings:** Add comments explaining non-standard values
3. **Version control:** Track configuration changes with your code
4. **Validate early:** Run validation before long processing jobs

### Performance Optimization

```json
{
  "general": {
    "debug": false            // Disable debug visualization in production
  },
  "debug": {
    "saved_artifact_type": "image",
    "save_composite_img": false   // Reduces memory usage
  },
  "log": {
    "log_to_console": false,  // Faster than console output
    "log_level": "WARNING"    // Reduce log volume
  }
}
```

### Development Settings

```json
{
  "general": {
    "debug": true             // Enable debug visualization
  },
  "debug": {
    "saved_artifact_type": "both",   // Helpful for analysis
    "save_composite_img": true,
    "relative_path": "debug/experiment_name"
  },
  "log": {
    "log_level": "DEBUG",    // Maximum detail
    "log_to_console": true   // Immediate feedback
  }
}
```

---

## 📖 Related Documentation

- **[DEBUG_SYSTEM_GUIDE.md](DEBUG_SYSTEM_GUIDE.md)** - Debug visualization system
- **[LOGGING_CONFIGURATION.md](LOGGING_CONFIGURATION.md)** - Detailed logging setup
- **[SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)** - Overall system architecture

*This configuration system provides type safety, validation, and flexibility for both production and research use.*
