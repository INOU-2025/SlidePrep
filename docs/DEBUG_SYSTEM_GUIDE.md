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
- **`DetectionDrawer`** (`utils/debug/detection_drawer.py`): Specialized for grid detection step debugging (now expects results and metadata, not legacy objects)

**Import Structure:**
```python
# Import from individual modules (recommended)
from utils.debug.base_drawer import BaseDrawer
from utils.debug.detection_drawer import DetectionDrawer

# Or import from the debug package (convenience)
from utils.debug import BaseDrawer, DetectionDrawer
```


### Debugger Integration

The `Debugger` class provides automatic drawer integration:

```python
# Automatic drawer integration - preferred approach
debugger.save_debug_image("grid_detection", "output.png", image, results, metadata)
```


## DetectionDrawer

### Purpose
Visualizes grid line detection results by drawing contours and annotations on the original image, using the new result and metadata structure.

### Features
- **Contour visualization**: Color-coded contours based on result status (now determined by metadata/config)
- **Rotated bounding boxes**: Shows detected grid line boundaries
- **Automatic integration**: Works seamlessly with debugger system

### Usage
```python
# Automatic integration (recommended)
debugger.save_debug_image("grid_detection", "output.png", image, results, metadata)

# Manual usage (advanced)
drawer = debugger.create_drawer("grid_detection")
result_image = drawer.draw(image, results, metadata)
```

### Input Data Format
The DetectionDrawer now expects:
- `results`: List of detected grid lines or contours (structure defined by the new pipeline)
- `metadata`: Dictionary containing configuration and status info (e.g., thresholds, accepted/rejected status)

Color mapping and status assignment are now handled via metadata/config, not legacy enums.

This mapping is handled automatically by the `DetectionStatus.get_color()` utility method.

## Creating Custom Drawers

The debug system uses a registry-based factory pattern that allows you to easily add new drawer types for custom analysis steps.

#### 1. Implement BaseDrawer Interface
```python
from utils.debug.base_drawer import BaseDrawer
from typing import Optional, Any
import numpy as np
import cv2

class CustomAnalysisDrawer(BaseDrawer):
    def __init__(self, enabled: bool = True):
        super().__init__(enabled)
    
    def draw(self, image: np.ndarray, results: Any = None, metadata: Any = None) -> Optional[np.ndarray]:
        """
        Draw analysis results on the image.
        
        Args:
            image: Base image to draw on
            results: Analysis results to visualize
            metadata: Additional metadata (e.g., confidence scores)
            
        Returns:
            Enhanced image with analysis visualizations
        """
        if results is None:
            return None
            
        try:
            # Create working copy
            overlay = image.copy()
            
            # Draw your analysis results
            # Example: draw confidence score
            if metadata and 'confidence' in metadata:
                confidence = metadata['confidence']
                cv2.putText(overlay, f"Confidence: {confidence:.2f}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            return overlay
        except Exception:
            # Always fail gracefully
            return image.copy() if image is not None else None
```
### 2. Register the Custom Drawer
```python
from core.debugger import Debugger

# Register your custom drawer with the global registry
Debugger.register_drawer("custom_analysis", CustomAnalysisDrawer)

# Now you can use it anywhere in your code
debugger.save_debug_image("custom_analysis", "output.png", image, analysis_results, {"confidence": 0.95})
```

### Best Practices

1. **Follow BaseDrawer Contract**: Always inherit from `BaseDrawer` and implement the `draw()` method
2. **Use Descriptive Names**: Choose clear, descriptive names for your drawer types in the registry
3. **Handle Edge Cases**: Ensure your drawer handles invalid inputs gracefully
4. **Fail Gracefully**: Wrap drawing code in try-except to avoid disrupting the main pipeline
5. **Use Debugger Integration**: Prefer `debugger.save_debug_image()` over manual drawer usage

## Configuration

Debug visualization is controlled by the debug configuration:

```json
{
  "debug": {
    "enabled": true,
    "save_composite": false,
    "output_dir": "/path/to/debug/output"
  }
}
```

- **`enabled`**: Master switch for debugging features
- **`save_composite`**: Create side-by-side comparisons when possible
- **`output_dir`**: Directory where debug images are saved

## Usage Patterns

### Step Integration
```python
# In your pipeline step
class MyStep(PipelineStep):
    def run(self, data):
        # Process data
        result = self.process(data)
        
        # Debug output - automatic drawer integration
        self.debugger.save_debug_image(
            "my_step", 
            f"{filename}_my_step.png", 
            data, 
            result, 
            {"processing_time": elapsed_time}
        )
        
        return result
```

### Test Runner Integration
```python
# Test runners automatically benefit from drawer system
runner = StepTestRunner(config_path)
step = MyStep(config=runner.cfg.my_config, debugger=runner.debugger, logger=runner.logger)
runner.run_on_directory(step, "my_step_results")
```

## Best Practices

### Error Handling
All drawer methods should fail silently to avoid disrupting the main pipeline:

```python
def draw(self, image, results=None, metadata=None):
    try:
        # visualization code
        return enhanced_image
    except Exception:
        # Return copy of original image or None
        return image.copy() if image is not None else None
```

### Performance
- Debugger controls when drawers are used based on debug configuration
- Return `None` from `draw()` when there's nothing to visualize
- Use efficient drawing operations in `draw()` methods
- Use automatic debugger integration to avoid manual file handling

### File Naming
Use consistent naming patterns for debug files:
- `{original_filename}_{step_name}.png`
- Example: `sample001_grid_detection.png`

### Memory Management
- Drawers should not store images as instance variables
- Use `image.copy()` only when necessary for modifications
- Return `None` from `draw()` when disabled to avoid memory allocation

## Troubleshooting

### Common Issues

**Debug images not created**
- Check `debug.enabled` in config
- Verify `output_dir` exists and is writable
- Check that drawer is registered: `Debugger.get_registered_drawers()`
- Ensure `debugger.save_debug_image()` is called with correct step key

**No drawer integration**
- Verify drawer is registered for the step: `Debugger.register_drawer("step_key", DrawerClass)`
- Check step key matches between registration and `save_debug_image()` call
- Images will save as plain images if no drawer is registered

**Poor visualization quality**
- Ensure drawer `draw()` method handles image format correctly
- Check that results/metadata match what drawer expects
- Verify color values are in correct range (0-255 for uint8)

**Performance issues**
- Disable debugging in production: `debug.enabled: false`
- Ensure drawers return `None` when disabled
- Use efficient drawing operations in `draw()` methods

---

## 📖 Related Documentation

- **[README.md](README.md)** - Documentation index and quick start
- **[SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)** - System architecture and development guide
- **[BINARIZATION_METHODS_GUIDE.md](BINARIZATION_METHODS_GUIDE.md)** - Complete binarization methods guide

*This debug system helps developers understand and troubleshoot pipeline behavior.*
