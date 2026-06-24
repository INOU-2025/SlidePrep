# AGENTS.md

## Project Overview
SlidePrep is a Python-based pipeline for processing microscopy image tiles and generating whole slide images. The system focuses on removing grid artifacts and preparing images for stitching.

## Repository Structure
- `main.py` – entry point for the production pipeline.
- `config/` – configuration schemas and default settings.
- `src/`
  - `core/` – pipeline infrastructure (context, bootstrap, logger).
  - `steps/` – individual processing steps like binarization and grid detection.
  - `utils/` – helper modules and research methods.
- `scripts/` – step-level test runners and benchmarking (`test_runner.py`, `benchmark_pipeline.py`).
- `docs/` – project documentation and guides.
- `data/`, `models/`, `training/` – datasets, trained models, and training utilities.
- `requirements.txt`, `environment.yml` – dependency listings for pip and conda.

## Coding Guidelines
- Target **Python 3.12.11**.
- Follow **PEP8** style; include type hints and module/function docstrings.
- Keep functions small and steps modular.
- Use absolute imports from `src`.
- Update configuration schemas and documentation when introducing new settings.

## Testing & Verification
- Run the test suite with `pytest tests/` from the repository root.
- The DZI test is skipped automatically if `vips` is not installed (`vips` is required for the web pipeline but not for CLI use).

## Documentation
- Update files in `docs/` when altering behavior or exposing new features.
- Provide code examples or usage notes in the README when appropriate.

## Dependencies
- Add new dependencies to both `environment.yml` and `requirements.txt`.
- Ensure optional tools are documented and pinned to specific versions when possible.

## Commit Messages
- Use clear, descriptive commit messages (e.g., `feat: add new grid removal method`).