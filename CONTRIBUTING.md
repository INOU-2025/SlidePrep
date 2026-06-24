# Contributing to SlidePrep

Thank you for your interest in contributing. This document covers the development environment, code standards, testing workflow, and pull-request process.

---

## Development environment

**Python version:** 3.12.11 (pinned — do not use 3.13+ until dependencies are validated)

### Setting up

```bash
# Clone the repository
git clone <repo-url>
cd SlidePrep

# Create the conda environment (CPU/macOS)
conda env create -f environment.yml -n slideprep
conda activate slideprep
pip install --no-deps simple-lama-inpainting==0.1.2

# Linux with NVIDIA GPU
conda env create -f environment-cuda.yml -n slideprep
conda activate slideprep
pip install --no-deps simple-lama-inpainting==0.1.2
```

> **GCC 14+ (Linux):** export `CFLAGS="-Wno-error=incompatible-pointer-types"` before creating the environment. See the README for details.

**Java** is required by Ashlar:
```bash
# macOS
brew install openjdk

# Ubuntu/Debian
sudo apt install default-jdk
```

---

## Running the test suite

```bash
pytest tests/ -v
```

The DZI test is automatically skipped when `vips` is not installed — this is expected for local development without the full web stack.

Run a single test file:
```bash
pytest tests/test_pipeline.py -v
```

Run a single test:
```bash
pytest tests/test_binarization.py::test_combined_differential -v
```

---

## Code standards

### Style
- Follow **PEP 8**. Line length: 100 characters.
- Use `snake_case` for functions and variables, `PascalCase` for classes.

### Type hints
All public functions and methods must include type annotations (PEP 484):

```python
def run(self, data: Any) -> StepResult:
```

### Docstrings
Use Google-style docstrings for public classes and methods. Explain behaviour and purpose, not implementation. One-line docstrings are fine for trivial functions:

```python
def to_array(self) -> Any:
    """Return the step result as a raw data object."""
    return self.data
```

### Comments
Write comments only when the *why* is non-obvious. Do not comment what the code already says.

### No print statements
Use the logger (`self.log()`, `self.debug()`, etc. in pipeline steps; `logger.info()` elsewhere). `print()` is reserved for CLI entry points and test scripts.

---

## Adding a new pipeline step

See [docs/STEP_EXTENSION_GUIDE.md](docs/STEP_EXTENSION_GUIDE.md) for the complete six-file walkthrough, including the config model, `AppConfigManager` wiring, `build_default_pipeline()` insertion, and test runner script.

---

## Adding dependencies

Add new packages to **both** `environment.yml` and `requirements.txt`. Pin to a specific version where possible. If a dependency is only needed for a specific platform (e.g. CUDA), add it only to `environment-cuda.yml` and document that in the PR description.

Do not add packages that are already available through the conda base or that overlap with existing dependencies without first checking for conflicts.

---

## Updating documentation

- Update files in `docs/` whenever you change behaviour, add config fields, rename classes, or expose new features.
- Add a JSON example and parameter table in `docs/CONFIGURATION_GUIDE.md` for any new config section.
- If you add a new pipeline step, add it to the `docs/SYSTEM_OVERVIEW.md` step table and the project structure tree in `README.md`.
- Keep `config/README.md` in sync with any new files added to `config/` or `config/test/`.

---

## Commit messages

Use the conventional commits format:

```
feat: add sharpness enhancement step
fix: correct column-major tile index assignment
docs: document target_inclination_angles config field
refactor: extract ArtifactSink interface from Debugger
test: add unit test for OME-TIFF pixel size injection
chore: pin pillow to 10.4.0 in environment.yml
```

Keep the subject line under 72 characters. Use the body (separated by a blank line) for context that does not fit in the subject.

---

## Pull request process

1. Fork the repository and create a feature branch from `main`.
2. Make your changes, following the standards above.
3. Ensure `pytest tests/ -v` passes with no failures.
4. Run the step test script for any step you modified:
   ```bash
   python scripts/test_binarization.py config/test/binarization.json
   ```
5. Update documentation as described above.
6. Open a pull request against `main`. The description should explain *why* the change is needed, not just *what* changed.

---

## Reporting issues

Open a GitHub issue and include:
- SlidePrep version / git commit hash
- Python version and OS
- Minimal reproduction steps
- Full error traceback

For configuration problems, attach the config JSON (with paths anonymised if necessary).
