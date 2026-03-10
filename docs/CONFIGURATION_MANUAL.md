# Technical Manual: SlidePrep Configuration System

## Purpose

This manual is intended for developers onboarding to SlidePrep. It explains how the configuration system works, which sections compose a valid configuration, and how to create new configurations for both full pipeline execution and isolated step testing.

---

## 1. Configuration System Architecture

The configuration system is built on four core layers:

1. **Typed schema (Pydantic)** in `config/config_schema.py`.
2. **Application-level aggregate contract** in `api/schemas.py` (`AppConfig`).
3. **Configuration manager** in `src/core/app_config_manager.py`.
4. **Bootstrap and dependency-injection container** in `src/core/bootstrap.py`.

### Initialization flow

1. A JSON configuration file is loaded.
2. `AppConfigManager` maps each section to typed objects (`GeneralConfig`, `BinarizationConfig`, etc.).
3. Field-level and model-level validations are applied (paths, enums, numeric ranges, and so on).
4. `bootstrap()` registers config, logger, debugger, and context in the DI container.
5. `PipelineService` builds pipeline steps using those typed section objects.

This design removes fragile string-based access from business logic and centralizes validation and defaults in one place.

---

## 2. What a configuration is made of

A complete configuration is organized into JSON sections. Not all sections are required for all execution modes.

## 2.1 `general`

Global runtime settings:

- `input_path`: input file or directory.
- `output_path`: base output directory.
- `suffix_filter`: suffix filter for batch discovery.
- `output_suffix`: suffix appended to processed outputs.
- `log`: enables/disables logging.
- `debug`: enables/disables debug artifact generation.

## 2.2 `test` (optional, for isolated testing)

Overrides test execution paths without modifying `general`:

- `input_path`: test input location.
- `output_path`: test output location.
- `input_type`: `"image"` or `"data"`.
- `max_images`: optional processing cap.

> When `test.output_path` is defined, it is used as the base for test log/debug destinations.

## 2.3 Step sections

Each step owns an independent section:

- `binarization`
- `grid_detection`
- `grid_refinement`
- `inpainting`
- `img_conversion`
- `stitching`

Design rule: **each step consumes only its own config section**.

## 2.4 `log`

Logging behavior:

- `log_to_file`
- `log_to_console`
- `log_file_name`
- `log_level`
- `relative_path`

## 2.5 `debug`

Debug artifact persistence and output strategy:

- `saved_artifact_type`: `"image" | "data" | "both"`
- `save_composite_img`
- `save_aggregated_data`
- `input_result_file_name`
- `result_file_name`
- `relative_path`
- `artifact_sink`: `"local" | "memory"`

---

## 3. Validation and defaults

Validation happens when Pydantic models are instantiated. Examples:

- Input/mask/model paths must exist when provided.
- Enum-like fields (`input_type`, output formats, log levels) accept only valid values.
- Numeric constraints (such as overlap and thresholds) are validated explicitly.

If an optional section is missing, the system can:

- keep it as `None` for optional step usage, or
- apply safe defaults for specific sections (for example, stitching).

---

## 4. How to create a new configuration

## 4.1 Case A: full pipeline configuration

1. Copy `config/development.json` or `config/production.json`.
2. Set `general.input_path` and `general.output_path`.
3. Fill in the step parameters required by your target flow.
4. Define `log` and `debug` policies.
5. Run the pipeline from `main.py`.

Minimal example:

```json
{
  "general": {
    "input_path": "data/input",
    "output_path": "data/output",
    "suffix_filter": "_ch00",
    "output_suffix": "_processed",
    "log": true,
    "debug": false
  },
  "binarization": {
    "threshold_method": "combined_differential"
  },
  "img_conversion": {
    "format": "png",
    "mode": "RGB"
  },
  "log": {
    "log_to_file": true,
    "log_to_console": true,
    "log_file_name": "pipeline.log",
    "log_level": "INFO"
  },
  "debug": {
    "saved_artifact_type": "image",
    "save_composite_img": false,
    "save_aggregated_data": false,
    "artifact_sink": "local"
  }
}
```

## 4.2 Case B: configuration for single-step testing

1. Create a file under `config/test/` (for example, `my_step.json`).
2. Include `general` + `test`.
3. Include only the section for the step under evaluation.
4. Enable debug output and detailed logging.
5. Run the corresponding script in `src/scripts/`.

Minimal binarization test example:

```json
{
  "general": {
    "input_path": "data/raw",
    "output_path": "data/dev_out",
    "suffix_filter": "_raw",
    "output_suffix": "_bin",
    "log": true,
    "debug": true
  },
  "binarization": {
    "threshold_method": "combined_differential"
  },
  "test": {
    "input_path": "data/raw",
    "output_path": "data/test_out",
    "input_type": "image",
    "max_images": 20
  },
  "log": {
    "log_to_file": false,
    "log_to_console": true,
    "log_level": "DEBUG"
  },
  "debug": {
    "saved_artifact_type": "image",
    "save_composite_img": true,
    "save_aggregated_data": false,
    "artifact_sink": "local"
  }
}
```

---

## 5. Integration with `PipelineService` and steps

`PipelineService` builds the execution chain using the typed config returned by `AppConfigManager`. Current sequence:

1. `BinarizationStep`
2. `GridDetectionStep`
3. `GridRefinementStep`
4. `MaskCreationStep`
5. `InpaintingStep`
6. `ImgConversionStep`

To add a new step:

1. Add its configuration model to `config/config_schema.py`.
2. Expose it in `api/schemas.py` through `AppConfig`.
3. Extract and wire it in `AppConfigManager`.
4. Inject it when composing steps in `PipelineService._create_pipeline()`.
5. Add documentation and an example config under `config/test/`.

---

## 6. Recommended best practices

- Keep section names stable to avoid breaking scripts.
- Prefer safe defaults in schema + strict validation at runtime.
- Separate production and test paths to avoid artifact contamination.
- Version example configs in `config/test/` for reproducibility.
- Document every new field in `docs/CONFIGURATION_GUIDE.md` and `docs/README.md`.

---

## 7. Quick checklist

Before running:

- [ ] `general.input_path` exists.
- [ ] `output_path` is writable.
- [ ] Enum-like fields (`log_level`, `input_type`, formats) are valid.
- [ ] Model/mask paths exist when configured.
- [ ] Test configs define dedicated `test.input_path` and `test.output_path`.
- [ ] `debug` and `log` settings match your goal (diagnostics vs throughput).

With this approach, SlidePrep configuration stays modular, validatable, and extensible for both full pipeline execution and step-level testing.
