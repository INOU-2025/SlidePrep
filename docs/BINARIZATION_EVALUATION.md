# Binarization Method Evaluation

## Overview

The `evaluate_binarization_methods.py` script is a batch evaluation tool for
comparing binarization methods exposed by `BinarizationMethods`
(`src/utils/binarization/__init__.py`). It processes batches of images and
provides detailed analysis and statistics. Currently its `methods` list only
runs `combined_differential` (the production method); add entries to that
list to compare other `BinarizationMethods` methods (`global`, `otsu`,
`adaptive`, `multi_otsu`, `line_enhanced`, `morphological`) side by side.

## Purpose

This script is designed for:
- **Method Comparison**: Evaluate different binarization approaches
- **Batch Processing**: Process entire folders of images
- **Statistical Analysis**: Generate success rates and pixel distribution metrics
- **Quality Assessment**: Visual comparison through organized output structure

## Usage

```bash
python src/utils/binarization/evaluate_binarization_methods.py path/to/config.json
```

The config path is a required argument — there is no default.

## Output

The script generates:
- Method-specific output folders with processed images
- Detailed statistics including success/failure rates
- Pixel distribution analysis (white pixel percentages)
- Comprehensive processing reports

## Configuration

A ready-made evaluation config lives at `config/test/binarization.json`. Key
configuration sections:
- `general.input_path`: Source folder for images
- `general.output_path`: Base output directory
- `general.suffix_filter`: Optional file suffix filter
- `binarization.threshold_method`: Method used by the pipeline's
  `BinarizationStep` (currently only `combined_differential` is wired up
  there; see [BINARIZATION_METHODS_GUIDE.md](BINARIZATION_METHODS_GUIDE.md))

## Related tooling

- `scripts/test_binarization.py config/test/binarization.json` runs the
  production `BinarizationStep` through the shared `StepTestRunner` for a
  quick single-step smoke test.
- `tests/test_binarization.py` has unit tests for `BinarizationStep`
  (grayscale and RGB inputs).
