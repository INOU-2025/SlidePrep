# Debug System Guide

## 🐛 Overview

The SlidePrep pipeline includes a comprehensive debug visualization system. Each processing step has dedicated debug outputs that help developers understand and troubleshoot the pipeline behavior.

## 🏗️ Architecture

### Constructor-Injection Pattern

The debug system uses constructor injection: a `Drawer` and a `ResultWriter` are passed to `Debugger` at construction time. There is no global registry.

- **`Drawer`** (`src/utils/debug/drawer.py`): Abstract base class all drawers inherit from
- **`DetectionDrawer`** (`src/utils/debug/detection_drawer.py`): Specialized for grid detection step debugging
- **`ResultWriter`** (`src/utils/debug/result_writer.py`): Interface for persisting step data to disk
- **`Debugger`** (`src/core/debugger.py`): Coordinates image saving, result writing, and artifact routing

### Artifact sinks

`Debugger` routes all artifacts through an `ArtifactSink`:

- **`LocalArtifactSink`**: Writes images and data to a directory on disk (default)
- **`InMemoryArtifactSink`**: Keeps artifacts in memory for streaming or deferred upload

The sink is selected automatically from `debug.artifact_sink` in the config (`"local"` or `"memory"`), or can be injected directly.

### Result Writers

To persist step outputs in human-readable formats, attach a `ResultWriter` to the `Debugger`. Each writer implements a `write(path, results, metadata)` method. Call `debugger.save_results()` to invoke it.

**Import paths:**
```python
from src.utils.debug.drawer import Drawer
from src.utils.debug.detection_drawer import DetectionDrawer
from src.utils.debug.result_writer import ResultWriter

# Or via the package shorthand
from src.utils.debug import Drawer, DetectionDrawer, ResultWriter
```

### Debugger API

```python
# Construction — inject drawer and writer at creation time
debugger = Debugger(
    logger=logger,
    debug_config=debug_config,
    debug_enabled=True,
    drawer=DetectionDrawer(),       # optional
    writer=DetectionResultWriter(), # optional
)

# Save a debug visualization (drawer.draw() is called when a drawer is attached)
debugger.save_debug_image("output.png", image, results, metadata)

# Persist structured data (writer.write() is called when a writer is attached)
debugger.save_results("results.json", results, metadata)
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
# Via the debugger (drawer is called automatically when attached)
debugger.save_debug_image("output.png", image, results, metadata)

# Direct usage (advanced)
drawer = DetectionDrawer()
result_image = drawer.draw(image, results, metadata)
```

### Input Data Format
The DetectionDrawer now expects:
- `results`: List of detected grid lines or contours (structure defined by the new pipeline)
- `metadata`: Dictionary containing configuration and status info (e.g., thresholds, accepted/rejected status)

Color mapping and status assignment are handled via the metadata/config dictionary passed to `draw()`.

## Creating Custom Drawers

The debug system uses a registry-based factory pattern that allows you to easily add new drawer types for custom analysis steps.

#### 1. Implement Drawer Interface
```python
from src.utils.debug.drawer import Drawer
from typing import Optional, Any
import numpy as np
import cv2

class CustomAnalysisDrawer(Drawer):
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
### 2. Inject the Custom Drawer
```python
from src.core.debugger import Debugger

# Inject your custom drawer when constructing the Debugger
debugger = Debugger(
    logger=logger,
    debug_config=debug_config,
    debug_enabled=True,
    drawer=CustomAnalysisDrawer(),
)

# The drawer is called automatically
debugger.save_debug_image("output.png", image, analysis_results, {"confidence": 0.95})
```

### Best Practices

1. **Follow Drawer Contract**: Always inherit from `Drawer` and implement the `draw()` method
2. **Use Descriptive Names**: Choose clear, descriptive names for your drawer types in the registry
3. **Handle Edge Cases**: Ensure your drawer handles invalid inputs gracefully
4. **Fail Gracefully**: Wrap drawing code in try-except to avoid disrupting the main pipeline
5. **Use Debugger Integration**: Prefer `debugger.save_debug_image()` over manual drawer usage

## Configuration

Debug visualization is controlled by the debug configuration:

```json
{
  "debug": {
    "relative_path": "debug",      // Optional directory inside output path
    "saved_artifact_type": "both",
    "save_composite_img": false,
    "save_aggregated_data": true,
    "artifact_sink": "local"       // "local" or "memory"
  }
}
```

- **`relative_path`**: Optional directory inside the run's output where artifacts are stored
- **`saved_artifact_type`**: Specify whether to save images, data, or both
- **`save_composite_img`**: Create side-by-side comparisons when possible
- **`save_aggregated_data`**: Persist step results to `aggregated_data.json`
- **`artifact_sink`**: Choose storage backend. `local` writes to disk, while `memory` keeps artifacts in memory for streaming.

### Selecting a Storage Backend

**Local filesystem (default)**

```json
{
  "debug": {
    "artifact_sink": "local"
  }
}
```

Artifacts are written to the directory resolved by `relative_path`.

**In-memory streaming (e.g., cloud upload)**

```json
{
  "debug": {
    "artifact_sink": "memory"
  }
}
```

Artifacts are retained in memory and can be forwarded to a remote service such as S3 or Azure Blob storage.

## Usage Patterns

### Step Integration
```python
# In your pipeline step
class MyStep(PipelineStep):
    def run(self, data):
        # Process data
        result = self.process(data)
        
        # Debug output - drawer is called automatically when attached
        self.debugger.save_debug_image(
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

For every item processed, the runner attempts to find a source image with the
same filename in ``general.input_path`` and records its path in the pipeline
context. This lets steps retrieve the original image even when the provided
input is a mask or intermediate data. When ``test.input_type`` is set to
``"data"``, the runner reads JSON files from ``test.input_path`` instead of
images, still pairing them with the located source images to emulate full
pipeline execution.

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
- Check `general.debug` is set to `true` in config (this is the single source of truth for debug enablement)
- Verify the output directory is writable
- Ensure `debugger.save_debug_image()` is called with a non-empty filename

**No drawer integration**
- Verify a `Drawer` instance was passed to `Debugger(drawer=...)` at construction time
- If no drawer is attached, `save_debug_image()` saves the `results` array directly (no overlay)

**Poor visualization quality**
- Ensure drawer `draw()` method handles image format correctly
- Check that results/metadata match what drawer expects
- Verify color values are in correct range (0-255 for uint8)

**Performance issues**
- Disable debugging in production: set `general.debug` to `false` in config
- Ensure drawers return `None` when disabled
- Use efficient drawing operations in `draw()` methods

---

## 📖 Related Documentation

- **[README.md](README.md)** - Documentation index and quick start
- **[SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)** - System architecture and development guide
- **[BINARIZATION_METHODS_GUIDE.md](BINARIZATION_METHODS_GUIDE.md)** - Complete binarization methods guide

*This debug system helps developers understand and troubleshoot pipeline behavior.*
