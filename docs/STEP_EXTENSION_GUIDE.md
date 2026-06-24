# Step Extension Guide

This guide walks through adding a new processing step to the SlidePrep pipeline end-to-end. The pipeline is designed for extension: each step is a self-contained class, and wiring it in requires touching six files in a fixed order.

The guide uses a fictional `SharpnessStep` as the running example.

---

## Overview

| # | File | What to do |
|---|---|---|
| 1 | `src/config/schema.py` | Add a Pydantic config model |
| 2 | `src/config/__init__.py` | Export the new config class |
| 3 | `src/steps/sharpness.py` | Implement the step |
| 4 | `src/steps/__init__.py` | Export the new step class |
| 5 | `src/core/app_config_manager.py` | Extract the typed config section |
| 6 | `src/core/pipeline_service.py` | Insert the step into `build_default_pipeline()` |

Then optionally:

| # | File | What to do |
|---|---|---|
| 7 | `src/core/bootstrap.py` | Register shared resources (if the step needs them) |
| 8 | `config/test/sharpness.json` | Add an isolated test configuration |
| 9 | `scripts/test_sharpness.py` | Add a step-level test runner script |

---

## Step 1 — Config model (`src/config/schema.py`)

Add a Pydantic model at the bottom of the file, alongside the existing config classes:

```python
class SharpnessConfig(BaseModel):
    """Configuration for the sharpness enhancement step."""

    kernel_size: int = 3          # Sharpening kernel radius
    strength: float = 1.0         # Enhancement factor (0 = no change, >1 = stronger)

    @field_validator("kernel_size")
    @classmethod
    def _validate_kernel_size(cls, v: int) -> int:
        if v < 1 or v % 2 == 0:
            raise ValueError("kernel_size must be a positive odd integer")
        return v

    @field_validator("strength")
    @classmethod
    def _validate_strength(cls, v: float) -> float:
        if v < 0:
            raise ValueError("strength must be non-negative")
        return v
```

## Step 2 — Export the config (`src/config/__init__.py`)

Add the import and register the name in `__all__`:

```python
from .schema import (
    ...
    SharpnessConfig,   # ← add
)

__all__ = [
    ...
    "SharpnessConfig",   # ← add
]
```

## Step 3 — Implement the step (`src/steps/sharpness.py`)

```python
from typing import Any
import cv2
import numpy as np

from src.config import SharpnessConfig
from src.core.step import PipelineStep
from src.core.step_result import StepResult


class SharpnessStep(PipelineStep):
    """Pipeline step that applies unsharp masking to enhance image sharpness."""

    def __init__(self, config: SharpnessConfig) -> None:
        super().__init__(name="sharpness", config=config)

    def run(self, data: Any) -> StepResult:
        """Apply unsharp masking to the input image.

        Args:
            data: Grayscale or colour image as a numpy array.

        Returns:
            StepResult containing the sharpened image.
        """
        self._validate_image_input(data)

        self.debug(
            f"Applying sharpness enhancement "
            f"(kernel={self.config.kernel_size}, strength={self.config.strength})"
        )

        blurred = cv2.GaussianBlur(data, (self.config.kernel_size, self.config.kernel_size), 0)
        sharpened = cv2.addWeighted(data, 1 + self.config.strength, blurred, -self.config.strength, 0)

        self.debug("Sharpness enhancement completed successfully")
        return StepResult.from_array(sharpened)
```

**Key rules:**

- Always call `super().__init__(name="sharpness", config=config)`. The `name` string is what appears in log lines (`Step sharpness completed successfully`).
- Use `self._validate_image_input(data)` at the top of `run()` — it raises `TypeError`/`ValueError` for null or dimensionless inputs.
- Use `self.debug()`, `self.log()`, `self.warning()`, `self.error()` rather than `print()`. These are prefixed with `[Sharpness]` automatically.
- Return a `StepResult` — never a raw array.

### Accessing shared pipeline resources

If your step needs a resource that is expensive to load (like the LaMa model), register it in `bootstrap.py` (see step 7) and retrieve it from the container in `run()`:

```python
def run(self, data: Any) -> StepResult:
    my_model = self.container.resolve("my_model")   # loaded once, reused per tile
    ...
```

`self.container` is injected by the `Pipeline` executor before `run()` is called.

## Step 4 — Export the step (`src/steps/__init__.py`)

```python
from .sharpness import SharpnessStep   # ← add

__all__ = [
    ...
    "SharpnessStep",   # ← add
]
```

## Step 5 — Extract the config in `AppConfigManager` (`src/core/app_config_manager.py`)

Inside `_extract_config_values()`, add a line alongside the other config extractions:

```python
from src.config import SharpnessConfig   # add to imports at top of file

# Inside _extract_config_values():
self.sharpness_config = SharpnessConfig(
    **self._raw_config.get("sharpness", {})
)
```

This makes the config available as `config_manager.sharpness_config` throughout the pipeline.

## Step 6 — Wire into the pipeline (`src/core/pipeline_service.py`)

Insert your step into `build_default_pipeline()` at the desired position:

```python
from src.steps import (
    ...
    SharpnessStep,   # ← add
)

def build_default_pipeline(config: AppConfigManager, container: Container) -> Pipeline:
    steps = [
        BinarizationStep(config=config.binarization_config),
        GridDetectionStep(config=config.grid_detection_config),
        GridRefinementStep(config.grid_refinement_config),
        MaskCreationStep(),
        InpaintingStep(config=config.inpainting_config),
        SharpnessStep(config=config.sharpness_config),   # ← add (example: after inpainting)
        ImgConversionStep(config=config.img_conversion_config),
    ]
    return Pipeline(steps, container)
```

---

## Step 7 (optional) — Register shared resources (`src/core/bootstrap.py`)

If your step loads a model or other expensive resource, register it as a lazy singleton so it is loaded once and reused across tiles:

```python
from my_library import MyModel   # your dependency

# Inside bootstrap():
container.register_lazy_singleton("my_model", MyModel)
```

`register_lazy_singleton` defers construction until the first `container.resolve("my_model")` call.

---

## Step 8 — Test configuration (`config/test/sharpness.json`)

Create a minimal config that exercises only your step:

```json
{
  "general": {
    "input_path": "/path/to/test/images",
    "output_path": "/tmp/sharpness_test_output",
    "suffix_filter": ""
  },
  "sharpness": {
    "kernel_size": 3,
    "strength": 1.5
  },
  "log": {
    "log_to_console": true,
    "log_to_file": false,
    "log_level": "DEBUG"
  },
  "debug": {
    "saved_artifact_type": "image",
    "save_composite_img": true
  },
  "test": {
    "input_path": "/path/to/test/images",
    "output_path": "/tmp/sharpness_test_output",
    "input_type": "image",
    "max_images": 5
  }
}
```

## Step 9 — Test runner script (`scripts/test_sharpness.py`)

```python
import sys
from scripts.test_runner import StepTestRunner
from src.steps import SharpnessStep


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/test/sharpness.json"
    runner = StepTestRunner(config_path)
    step = SharpnessStep(config=runner.cfg.sharpness_config)
    runner.run_on_directory(step, "sharpness_results")


if __name__ == "__main__":
    main()
```

Run it with:

```bash
python scripts/test_sharpness.py config/test/sharpness.json
```

---

## Checklist

- [ ] `SharpnessConfig` added to `src/config/schema.py`
- [ ] Exported from `src/config/__init__.py`
- [ ] `SharpnessStep` implemented in `src/steps/sharpness.py`
- [ ] Exported from `src/steps/__init__.py`
- [ ] `self.sharpness_config` added to `AppConfigManager._extract_config_values()`
- [ ] Step inserted in `build_default_pipeline()`
- [ ] `config/test/sharpness.json` created
- [ ] `scripts/test_sharpness.py` created
- [ ] `config/README.md` updated with the new test config entry
- [ ] `docs/CONFIGURATION_GUIDE.md` updated with the new JSON section

---

## Related documentation

- [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) — full config reference and extension checklist
- [DEBUG_SYSTEM_GUIDE.md](DEBUG_SYSTEM_GUIDE.md) — adding debug visualizations to your step
- [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) — pipeline architecture and DI container
