# Binarization Method Evaluation

## Overview

The `evaluate_binarization_methods.py` script is a comprehensive evaluation tool for different binarization methods. It processes batches of images and provides detailed analysis and statistics.

## Purpose

This script is designed for:
- **Method Comparison**: Evaluate different binarization approaches
- **Batch Processing**: Process entire folders of images
- **Statistical Analysis**: Generate success rates and pixel distribution metrics
- **Quality Assessment**: Visual comparison through organized output structure

## Usage

```bash
# Use default test configuration
python scripts/evaluate_binarization_methods.py

# Use custom configuration
python scripts/evaluate_binarization_methods.py path/to/config.json
```

## Output

The script generates:
- Method-specific output folders with processed images
- Detailed statistics including success/failure rates
- Pixel distribution analysis (white pixel percentages)
- Comprehensive processing reports

## Configuration

Uses `config/test/binarization_test_config.json` by default. Key configuration sections:
- `general.input_path`: Source folder for images
- `general.output_path`: Base output directory
- `general.suffix_filter`: Optional file suffix filter
- `binarization.threshold_method`: Method to evaluate

## Future Development

This script name change reserves `test_binarization.py` for future unit testing of the `BinarizationStep` class specifically.
