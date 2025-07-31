# Debug System Guide

## 🐛 Overview

The SlidePrep pipeline includes a comprehensive debug visualization system. Each processing step has dedicated debug outputs that help developers understand and troubleshoot the pipeline behavior.

## 🏗️ Architecture

### Registry-Based Factory Pattern

The debug system uses a registry-based factory pattern for extensible drawer creation:

- **`BaseDrawer`**: Abstract base class that all drawers inherit from
- **`Debugger`**: Registry-based factory for creating step-specific drawers
- **Dynamic Registration**: New drawer types can be registered at runtime

**Benefits:**
- **Extensibility**: Add new drawer types without modifying core classes
- **Decoupling**: Drawer implementations are independent of the factory
- **Consistency**: Single, uniform interface for all drawer creation
- **Dynamic Discovery**: Create drawers by name for flexible configuration

### Built-in Drawer Types

The debug system includes specialized drawers for different pipeline steps, each organized in its own module:

- **`BaseDrawer`** (`utils/debug/base_drawer.py`): Abstract base class for all drawers
- **`BinarizationDrawer`** (`utils/debug/binarization_drawer.py`): Specialized for binarization step debugging  
- **`GridDetectionDrawer`** (`utils/debug/grid_detection_drawer.py`): Specialized for grid detection step debugging

**Import Structure:**
```python
# Import from individual modules (recommended)
from utils.debug.base_drawer import BaseDrawer
from utils.debug.binarization_drawer import BinarizationDrawer
from utils.debug.grid_detection_drawer import GridDetectionDrawer

# Or import from the debug package (convenience)
from utils.debug import BaseDrawer, BinarizationDrawer, GridDetectionDrawer
```

### Debugger Integration

The `Debugger` class provides registry-based drawer creation:

```python
# Generic registry-based creation
drawer = debugger.create_drawer("grid_detection", image)
drawer = debugger.create_drawer("binarization", image)
```

## BinarizationDrawer

### Purpose
Creates side-by-side comparisons of original grayscale images and their binarized results.

### Features
- **Side-by-side comparison**: Original and binarized images displayed together
- **Method information**: Shows which binarization method was used
- **Pixel statistics**: Displays percentage of white/black pixels
- **Automatic scaling**: Font size adapts to image dimensions

### Usage
```python
**Usage:**
```python
# In binarization step
drawer = debugger.create_drawer("binarization", gray_image)
drawer.set_binarized_image(binary_result, method_info="adaptive/gaussian")
drawer.save("image_binarization_debug.png")
```
```

### Output Format
```
[Original Image] | [Binarized Image (method)]
                 | White: 45.2% | Black: 54.8%
```

## GridDetectionDrawer

### Purpose
Visualizes grid line detection results by drawing contours, bounding boxes, and annotations on the original image.

### Features
- **Contour visualization**: Color-coded contours (green=accepted, yellow=maybe, red=rejected)
- **Bounding boxes**: Draw detection bounding boxes
- **Line overlays**: Draw detected grid lines
- **Text annotations**: Add custom labels and statistics

### Usage
```python
**Usage:**
```python
# In grid detection step
drawer = debugger.create_drawer("grid_detection", image)
drawer.set_horizontal_lines(h_lines)
drawer.set_vertical_lines(v_lines)
drawer.save("grid_detection_debug.png")
```
```

### Methods

#### `draw_contour(contour, accepted=False, maybe=False)`
- **Green**: `accepted=True` - Contour passes all criteria
- **Yellow**: `maybe=True` - Contour partially matches criteria  
- **Red**: Default - Contour rejected

#### `draw_box(box, color=(0,255,255), thickness=1)`
- Draw bounding box around detected regions

#### `draw_line(pt1, pt2, color=(255,0,0), thickness=2)`
- Draw line between two points

#### `add_text(text, position, color=(255,255,255))`
- Add text annotation at specified position

## Creating Custom Drawers

The debug system uses a registry-based factory pattern that allows you to easily add new drawer types for custom analysis steps.

#### 1. Implement BaseDrawer Interface
```python
from utils.debug.base_drawer import BaseDrawer
from typing import Optional
import numpy as np
import cv2

class CustomAnalysisDrawer(BaseDrawer):
    def __init__(self, input_image: np.ndarray, enabled: bool = True, output_dir: Optional[str] = None):
        super().__init__(enabled, output_dir)
        self.input_image = input_image
        self.analysis_result = None
        self.confidence_score = None
    
    def set_analysis_result(self, result: dict, confidence: float = 0.0):
        """Set the analysis result and confidence score."""
        self.analysis_result = result
        self.confidence_score = confidence
    
    def save(self, filename: str):
        """Create and save the debug visualization."""
        if not self.enabled or self.analysis_result is None:
            return
            
        try:
            # Create composite image with analysis visualization
            composite = self._create_composite_image()
            output_path = self._get_output_path(filename)
            cv2.imwrite(output_path, composite)
        except Exception as e:
            # Silently fail to avoid disrupting the main pipeline
            pass
    
    def _create_composite_image(self) -> np.ndarray:
        """Create the composite debug image."""
        # Implementation specific to your analysis visualization
        # Return composite image with original + analysis overlays
        return self.input_image  # Placeholder implementation
```

### 2. Register the Custom Drawer
```python
from core.debugger import Debugger

# Register your custom drawer with the global registry
Debugger.register_drawer("custom_analysis", CustomAnalysisDrawer)

# Now you can use it anywhere in your code
drawer = debugger.create_drawer("custom_analysis", image)
drawer.set_analysis_result(results, confidence=0.95)
drawer.save("custom_analysis_debug.png")
```

### Best Practices

1. **Follow BaseDrawer Contract**: Always inherit from `BaseDrawer` and implement required methods
2. **Use Descriptive Names**: Choose clear, descriptive names for your drawer types in the registry
3. **Handle Edge Cases**: Ensure your drawer handles invalid inputs gracefully
4. **Consistent Output**: Follow established naming conventions for debug output files
5. **Documentation**: Add docstrings explaining the purpose and usage of your custom drawer

## Configuration

Debug visualization is controlled by the debug configuration:

```json
{
  "debug": {
    "enabled": true,
    "visualization": true,
    "output_dir": "/path/to/debug/output"
  }
}
```

- **`enabled`**: Master switch for debugging features
- **`visualization`**: Enable/disable debug image creation
- **`output_dir`**: Directory where debug images are saved

## Best Practices

### Error Handling
All drawer methods should fail silently to avoid disrupting the main pipeline:

```python
def save(self, filename):
    try:
        # visualization code
    except Exception as e:
        # Log error if logger available, but don't raise
        pass
```

### Performance
- Only create visualizations when `enabled=True`
- Use `if self.enabled:` checks before expensive operations
- Avoid memory allocation when debugging is disabled

### File Naming
Use consistent naming patterns for debug files:
- `{original_filename}_{step_name}_debug.png`
- Example: `sample001.jpg_binarization_debug.png`

### Memory Management
- Copy input images only when debugging is enabled
- Clean up large arrays after saving
- Use appropriate image formats (PNG for debug, JPEG for space)

## Troubleshooting

### Common Issues

**Debug images not created**
- Check `debug.enabled` and `debug.visualization` in config
- Verify `output_dir` exists and is writable
- Check console/logs for error messages

**Poor visualization quality**
- Ensure input images are in correct format (BGR for color, grayscale for BinarizationDrawer)
- Check font scaling for text readability
- Verify color values are in correct range (0-255)

**Performance issues**
- Disable debugging in production: `debug.visualization: false`
- Use smaller images for testing
- Limit number of debug annotations per image

---

## 📖 Related Documentation

- **[README.md](README.md)** - Documentation index and quick start
- **[SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)** - System architecture and development guide
- **[BINARIZATION_METHODS_GUIDE.md](BINARIZATION_METHODS_GUIDE.md)** - Complete binarization methods guide

*This debug system helps developers understand and troubleshoot pipeline behavior.*
