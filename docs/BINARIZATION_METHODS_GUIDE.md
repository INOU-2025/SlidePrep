# Binarization Methods Guide

## 🎯 Overview

The `utils.binarization` package provides a comprehensive collection of image binarization (thresholding) methods for research, experimentation, and specialized use cases. While the production system uses the Combined Differential method automatically, this utility gives you direct access to all available methods.

## 🚀 Quick Start

### Basic Usage

```python
from src.utils.binarization import BinarizationMethods, ThresholdMethod
import cv2

# Load your image
image = cv2.imread('path/to/image.png', cv2.IMREAD_GRAYSCALE)

# Initialize the methods utility
methods = BinarizationMethods()

# Apply a specific method
binary_result = methods.apply_otsu_threshold(image)

# Or use the generic interface
binary_result = methods.apply_method(ThresholdMethod.OTSU, image)
```

### With Debug Output

```python
# Get debug information during processing
def debug_print(message):
    print(f"DEBUG: {message}")

methods = BinarizationMethods(debug_callback=debug_print)
binary_result = methods.apply_combined_differential_threshold(image)
```

## Available Methods

### 1. Global Thresholding (`global`)
**Description**: Fixed threshold value  
**Use Case**: Simple binary separation with known threshold  

```python
# Basic usage
binary = methods.apply_global_threshold(image, threshold=127)

# With inversion
binary = methods.apply_global_threshold(image, threshold=100, invert=True)

# Using generic interface
binary = methods.apply_method(ThresholdMethod.GLOBAL, image, threshold=120)
```

**Parameters**:
- `threshold` (int): Threshold value (0-255), default=127
- `invert` (bool): If True, dark regions become background, default=False

### 2. Otsu Automatic (`otsu`)
**Description**: Automatic threshold selection using Otsu's method  
**Use Case**: Bimodal intensity distributions  

```python
# Basic usage
binary = methods.apply_otsu_threshold(image)

# With inversion
binary = methods.apply_otsu_threshold(image, invert=True)
```

**Parameters**:
- `invert` (bool): If True, dark regions become background, default=False

### 3. Adaptive Thresholding (`adaptive`)
**Description**: Local threshold based on neighborhood statistics  
**Use Case**: Varying illumination conditions  

```python
# Gaussian adaptive (recommended)
binary = methods.apply_adaptive_threshold(image, method="gaussian", block_size=15, c_constant=5)

# Mean adaptive
binary = methods.apply_adaptive_threshold(image, method="mean", block_size=11, c_constant=2)

# With different threshold type
binary = methods.apply_adaptive_threshold(image, method="gaussian", thresh_type="binary_inv")
```

**Parameters**:
- `method` (str): "gaussian" or "mean", default="gaussian"
- `thresh_type` (str): "binary" or "binary_inv", default="binary"
- `block_size` (int): Neighborhood size for threshold calculation, default=11
- `c_constant` (float): Constant subtracted from mean, default=2
- `invert` (bool): Apply additional inversion, default=False

### 4. Multi-Otsu Thresholding (`multi_otsu`)
**Description**: Multi-level Otsu for multiple intensity classes  
**Use Case**: Images with multiple intensity regions  

```python
# 3-class thresholding (background, grid, content)
binary = methods.apply_multi_otsu_threshold(image, classes=3)

# 4-class thresholding
binary = methods.apply_multi_otsu_threshold(image, classes=4)
```

**Parameters**:
- `classes` (int): Number of threshold classes, default=3
- `invert` (bool): If True, dark regions become background, default=False

**Requirements**: scikit-image package (falls back to regular Otsu if not available)

### 5. Line-Enhanced Thresholding (`line_enhanced`)
**Description**: Enhanced detection of linear structures  
**Use Case**: Grid lines and linear patterns  

```python
# For thick grid lines (21px width, 2° rotation)
binary = methods.apply_line_enhanced_threshold(image, kernel_length=21, rotation_angle=2.0)

# For thinner lines
binary = methods.apply_line_enhanced_threshold(image, kernel_length=15, rotation_angle=0)
```

**Parameters**:
- `kernel_length` (int): Length of line detection kernel, default=21
- `rotation_angle` (float): Rotation angle in degrees, default=2.0
- `invert` (bool): If True, dark regions become background, default=False

### 6. Morphological Thresholding (`morphological`)
**Description**: Otsu followed by morphological operations  
**Use Case**: Noise reduction and shape refinement  

```python
# Closing operation (fills gaps)
binary = methods.apply_morphological_threshold(image, operation="close", kernel_size=5)

# Opening operation (removes noise)
binary = methods.apply_morphological_threshold(image, operation="open", kernel_size=3)

# Other operations
binary = methods.apply_morphological_threshold(image, operation="gradient", kernel_size=7)
```

**Parameters**:
- `operation` (str): "open", "close", "gradient", "tophat", "blackhat", default="close"
- `kernel_size` (int): Size of morphological kernel, default=3
- `invert` (bool): If True, dark regions become background, default=False

### 7. Combined Differential (`combined_differential`) ⭐ **Production Method**
**Description**: Multi-Otsu with spurious element removal  
**Use Case**: Thick grid detection with cellular content removal  

```python
# Production method - no parameters needed
binary = methods.apply_combined_differential_threshold(image)

# This is the same method used in production binarization step
```

**Parameters**: None (uses optimized production parameters internally)

## Method Information and Discovery

### Get Available Methods
```python
methods = BinarizationMethods()

# List all method names
available = methods.get_available_methods()
print(f"Available methods: {available}")
# Output: ['global', 'otsu', 'adaptive', 'multi_otsu', 'line_enhanced', 'morphological', 'combined_differential']
```

### Get Method Information
```python
# Get detailed information about a method
info = methods.get_method_info(ThresholdMethod.COMBINED_DIFFERENTIAL)
print(f"Description: {info['description']}")
print(f"Use case: {info['use_case']}")
print(f"Parameters: {info['parameters']}")

# Example output:
# Description: Production method: Multi-Otsu with spurious element removal
# Use case: Thick grid detection with cellular content removal
# Parameters: []
```

### Method Comparison
```python
# Compare multiple methods on the same image
methods_to_test = [
    ThresholdMethod.OTSU,
    ThresholdMethod.MULTI_OTSU,
    ThresholdMethod.COMBINED_DIFFERENTIAL
]

for method in methods_to_test:
    binary = methods.apply_method(method, image)
    foreground_pixels = np.sum(binary == 0)
    coverage = (foreground_pixels / binary.size) * 100
    print(f"{method.value}: {coverage:.2f}% foreground coverage")
```

## Batch Evaluation

Use the evaluation script to compare methods across a folder of images:

```bash
# Use the default test configuration
python src/utils/binarization/evaluate_binarization_methods.py

# Use a custom configuration
python src/utils/binarization/evaluate_binarization_methods.py path/to/config.json
```

The script generates method-specific output folders, success/failure rates, and pixel-distribution statistics. See [`docs/BINARIZATION_EVALUATION.md`](BINARIZATION_EVALUATION.md) for full details.

## Integration with Production System

### Current Production Usage
The production pipeline uses Combined Differential automatically via `BinarizationStep`:

```python
from src.steps import BinarizationStep
from src.config import BinarizationConfig

# This automatically uses Combined Differential
config = BinarizationConfig()  # threshold_method="combined_differential" by default
step = BinarizationStep(config)
result = step.run(image_array)  # Returns StepResult
binary_image = result.to_array()
```

> **Note:** `BinarizationStep` currently only implements `"combined_differential"`.
> Passing any other `threshold_method` value will raise a `ValueError` at runtime.

### Using Different Methods (Research / Utility Use)
To use any of the 7 available thresholding algorithms, call `BinarizationMethods`
directly — these are not routed through `BinarizationStep`:

```python
from src.utils.binarization import BinarizationMethods, ThresholdMethod

methods = BinarizationMethods()

# Otsu
result = methods.apply_otsu_threshold(your_image)

# Or use the generic interface with any ThresholdMethod enum value
result = methods.apply_method(ThresholdMethod.MULTI_OTSU, your_image)
result = methods.apply_method(ThresholdMethod.LINE_ENHANCED, your_image, kernel_length=21)
```

## Best Practices

### Method Selection Guidelines

1. **For thick grid detection (production)**: Use `combined_differential`
2. **For simple binary separation**: Use `global` with appropriate threshold
3. **For automatic thresholding**: Use `otsu` for bimodal images
4. **For uneven illumination**: Use `adaptive` with gaussian method
5. **For complex multi-class images**: Use `multi_otsu`
6. **For emphasizing linear structures**: Use `line_enhanced`
7. **For noisy images**: Use `morphological` with closing operation

### Parameter Tuning Tips

1. **Block size for adaptive**: Should be odd and larger than object features
2. **C constant for adaptive**: Increase for more selective thresholding
3. **Kernel length for line-enhanced**: Should match expected line width
4. **Rotation angle**: Set to match your grid rotation (usually 0-5°)
5. **Morphological kernel size**: Start small (3-5) and increase if needed

### Performance Considerations

1. **Fastest**: `global`, `otsu`
2. **Moderate**: `adaptive`, `morphological`
3. **Slower**: `multi_otsu`, `line_enhanced`, `combined_differential`

Choose simpler methods for batch processing of many images.

## Troubleshooting

### Common Issues

1. **All black or all white result**:
   - Try the `invert` parameter
   - Check if your image has sufficient contrast
   - Use `otsu` method first to test

2. **scikit-image not available error**:
   - Install with: `pip install scikit-image`
   - Or accept fallback to regular Otsu for multi-Otsu

3. **Poor grid detection**:
   - Try `line_enhanced` with appropriate kernel length
   - Use `combined_differential` for thick grids with cellular content
   - Adjust rotation angle to match your grid

4. **Too much noise in result**:
   - Use `morphological` with "open" operation
   - Try `adaptive` with larger block size
   - Use `combined_differential` which includes noise removal

### Debug Information

Enable debug output to understand what's happening:

```python
def my_debug(msg):
    print(f"🔍 {msg}")

methods = BinarizationMethods(debug_callback=my_debug)
result = methods.apply_combined_differential_threshold(image)
```

This will show:
- Threshold values computed
- Polarity corrections applied
- Component analysis results
- Morphological operations performed

## Examples

### Example 1: Grid Detection Comparison
```python
import cv2
import numpy as np
from src.utils.binarization import BinarizationMethods, ThresholdMethod

# Load your grid image
image = cv2.imread('grid_image.png', cv2.IMREAD_GRAYSCALE)
methods = BinarizationMethods()

# Test different methods for grid detection
grid_methods = [
    ThresholdMethod.OTSU,
    ThresholdMethod.MULTI_OTSU,
    ThresholdMethod.LINE_ENHANCED,
    ThresholdMethod.COMBINED_DIFFERENTIAL
]

for method in grid_methods:
    if method == ThresholdMethod.LINE_ENHANCED:
        binary = methods.apply_method(method, image, kernel_length=21, rotation_angle=2.0)
    else:
        binary = methods.apply_method(method, image)
    
    # Analyze results
    coverage = (np.sum(binary == 0) / binary.size) * 100
    print(f"{method.value}: {coverage:.2f}% grid coverage")
    
    # Save result
    cv2.imwrite(f'result_{method.value}.png', binary)
```

### Example 2: Adaptive Method for Uneven Lighting
```python
# For images with uneven illumination
image = cv2.imread('uneven_lighting.png', cv2.IMREAD_GRAYSCALE)
methods = BinarizationMethods()

# Try different adaptive parameters
configs = [
    {"block_size": 11, "c_constant": 2},
    {"block_size": 15, "c_constant": 5},
    {"block_size": 21, "c_constant": 8}
]

for i, config in enumerate(configs):
    binary = methods.apply_adaptive_threshold(image, **config)
    cv2.imwrite(f'adaptive_{i+1}.png', binary)
```

### Example 3: Method Selection Based on Image Analysis
```python
def select_best_method(image):
    methods = BinarizationMethods()
    
    # Analyze image characteristics
    mean_intensity = np.mean(image)
    std_intensity = np.std(image)
    
    if std_intensity < 30:
        # Low contrast - use adaptive
        return methods.apply_adaptive_threshold(image, block_size=15)
    elif mean_intensity < 100:
        # Dark image - might need inversion
        return methods.apply_otsu_threshold(image, invert=True)
    else:
        # Normal image - use production method
        return methods.apply_combined_differential_threshold(image)

# Use the selector
image = cv2.imread('unknown_image.png', cv2.IMREAD_GRAYSCALE)
result = select_best_method(image)
```

---

## 📖 Related Documentation

- **[README.md](README.md)** - Documentation index and quick start
- **[SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)** - System architecture and development guide  
- **[DEBUG_SYSTEM_GUIDE.md](DEBUG_SYSTEM_GUIDE.md)** - Debug visualization system

*This comprehensive guide covers all aspects of using the binarization methods utility.*
