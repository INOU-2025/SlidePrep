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
  "log": {         // Logging configuration
    // File/console output and levels
  },
  "debug": {       // Debug visualization settings
    // Output directories and options
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

### Logging Configuration

Controls logging output and verbosity:

```json
{
  "log": {
    "log_to_file": true,                // Enable file logging
    "log_to_console": false,            // Enable console logging
    "log_file_name": "app.log",         // Log filename
    "log_level": "INFO",                // Logging level
    "output_dir": "logs"                // Log output directory
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
    "output_dir": "debug_output",       // Debug output directory
    "save_composite": false             // Save side-by-side comparisons
  }
}
```

**Debug Options:**
- Debug enablement is controlled by `general.debug` (single source of truth)
- `save_composite`: Creates before/after comparison images
- `output_dir`: All debug images saved here

## 📁 Configuration Files

### Main Configurations

**File:** `config/production.json`
- **Purpose:** Production-optimized configuration
- **Usage:** `python main.py --config config/production.json`
- **Settings:** Optimized for production (debug=false, minimal logging, WARNING level)

**File:** `config/development.json`
- **Purpose:** Development-friendly configuration
- **Usage:** `python main.py --config config/development.json`
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
# Use default configuration
python main.py --input /path/to/images

# Use production configuration (optimized)
python main.py --config config/production.json

# Use development configuration (debug-friendly)
python main.py --config config/development.json

# Use custom configuration
python main.py --config /path/to/custom_config.json

# Override specific settings
python main.py --input /path/to/images --suffix "_ch00"
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
    "save_composite": false   // Reduces memory usage
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
    "save_composite": true,   // Helpful for analysis
    "output_dir": "debug_output/experiment_name"
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
