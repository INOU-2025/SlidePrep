# Debug System Guide

## 🐛 Overview

The SlidePrep pipeline includes a comprehensive debug visualization system. Each processing step has dedicated debug outputs that help developers understand and troubleshoot the pipeline behavior.

## 🏗️ Architecture

### Base Classes

- **`BaseDrawer`**: Abstract base class that all drawers inherit from
- **`BinarizationDrawer`**: Specialized for binarization step debugging
- **`GridDetectionDrawer`**: Specialized for grid detection step debugging

### Debugger Integration

The `Debugger` class provides factory methods to create appropriate drawers for each step:

```python
# For binarization step
drawer = debugger.create_binarization_drawer(original_image)

# For grid detection step  
drawer = debugger.create_grid_detection_drawer(overlay_image)
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
# In binarization step
drawer = debugger.create_binarization_drawer(gray_image)
drawer.set_binarized_image(binary_result, method_info="adaptive/gaussian")
drawer.save("image_binarization_debug.png")
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
# In grid detection step
drawer = debugger.create_grid_detection_drawer(bgr_image)
drawer.draw_contour(contour, accepted=True)
drawer.draw_box(bounding_box, color=(0, 255, 0))
drawer.add_text("Grid line detected", (10, 30))
drawer.save("image_grid_detection_debug.png")
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

## Adding New Drawers

To create a drawer for a new processing step:

### 1. Create Drawer Class
```python
class NewStepDrawer(BaseDrawer):
    def __init__(self, input_data, enabled=True, output_dir=None):
        super().__init__(enabled, output_dir)
        self.input_data = input_data
        
    def save(self, filename):
        if not self.enabled:
            return
        # Create visualization
        # Save using self._get_output_path(filename)
```

### 2. Add Factory Method to Debugger
```python
def create_new_step_drawer(self, input_data):
    return NewStepDrawer(input_data, enabled=self._visualization_active, output_dir=self._output_dir)
```

### 3. Use in Processing Step
```python
def run(self, ctx):
    # ... processing logic ...
    
    if self.debugger and self.debugger.is_enabled():
        drawer = self.debugger.create_new_step_drawer(input_data)
        # ... add visualizations ...
        drawer.save(f"{filename}_debug.png")
```

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
