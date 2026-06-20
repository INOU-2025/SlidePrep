# Benchmarking Guide

`scripts/benchmark_pipeline.py` measures SlidePrep end-to-end and per-stage
processing time to support the SoftwareX paper timing claims (Scenario A /
Scenario B).

## Prerequisites

The pipeline config passed to the script must have debug logging enabled so
the per-stage breakdown can be parsed from the log file:

```json
{
  "debug": {
    "enabled": true,
    "log_to_file": true
  },
  "log": {
    "relative_path": "pipeline.log"
  }
}
```

Without `debug.enabled`, end-to-end wall-clock times are still collected but
the per-stage breakdown table will be empty. The script prints a warning in
that case.

## Usage

Run from the project root (the same directory as `main.py`):

```bash
# GPU benchmark — 3 timed runs (default)
python scripts/benchmark_pipeline.py config/production.json

# More repeats for tighter statistics
python scripts/benchmark_pipeline.py config/production.json --repeats 5

# CPU-only (disables CUDA via CUDA_VISIBLE_DEVICES='')
python scripts/benchmark_pipeline.py config/production.json --cpu-only

# Both CPU and GPU — produces a speedup comparison
python scripts/benchmark_pipeline.py config/production.json --both

# Explicit log path (overrides what's in the config)
python scripts/benchmark_pipeline.py config/production.json --log-path logs/pipeline.log
```

### CLI flags

| Flag | Default | Description |
|------|---------|-------------|
| `config` | *(required)* | Path to pipeline config JSON |
| `--repeats N` | `3` | Number of timed runs per mode |
| `--gpu-only` | on | GPU benchmark (default when no mode flag given) |
| `--cpu-only` | off | CPU-only benchmark (`CUDA_VISIBLE_DEVICES=''`) |
| `--both` | off | Run CPU then GPU; prints speedup factor |
| `--log-path PATH` | read from config | Override log file path |

## How it works

1. **Warm-up run** — one unrecorded run executes first to load model weights
   and warm the disk cache. This run is excluded from all statistics.
2. **Timed runs** — `main.py` is invoked N times via `subprocess`. Wall-clock
   time is measured with `time.perf_counter()` around each subprocess call.
3. **Per-stage parsing** — after the final run, the pipeline's own debug log
   is parsed for lines of the form:
   ```
   2026-06-15 12:57:47,666 DEBUG Step binarization completed successfully
   ```
   These lines are emitted by `src/core/logger.py` with no added
   instrumentation. Consecutive timestamps are differenced to produce
   per-tile stage durations.

## Output

### Console summary

```
=== Benchmarking mode=gpu on config/production.json ===
  Warm-up run (not recorded)...
  Run 1/3... 42.3s
  Run 2/3... 41.8s
  Run 3/3... 42.1s

============================================================
BENCHMARK SUMMARY
============================================================

[GPU] median=42.1s mean=42.1s stdev=0.3s (n=3 runs)
  Per-stage breakdown (per-tile, from debug log):
    inpainting           mean=1.243s/tile  (38.2% of per-tile time, n=24 tiles)
    binarization         mean=0.891s/tile  (27.4% of per-tile time, n=24 tiles)
    detection            mean=0.754s/tile  (23.2% of per-tile time, n=24 tiles)
    ...

GPU speedup: 3.42x (70.8% time reduction)   ← only shown with --both
```

### JSON report

A full machine-readable report is written to
`benchmark_results/<YYYYMMDD_HHMMSS>_benchmark.json`:

```json
{
  "timestamp": "2026-06-15T13:01:22.441",
  "config": "config/production.json",
  "python": "3.11.9 ...",
  "modes": {
    "gpu": {
      "mode": "gpu",
      "repeats": 3,
      "wall_times_s": [42.30, 41.80, 42.10],
      "median_s": 42.10,
      "mean_s": 42.07,
      "stdev_s": 0.25,
      "stage_breakdown": {
        "inpainting": {
          "mean_s": 1.243,
          "median_s": 1.231,
          "stdev_s": 0.041,
          "n_tiles": 24,
          "total_s": 29.832
        }
      }
    }
  },
  "gpu_speedup_factor": 3.42,
  "gpu_time_reduction_pct": 70.8
}
```

`gpu_speedup_factor` and `gpu_time_reduction_pct` are only present when
`--both` is used.

## Interpreting the results

- **Median over mean** — use `median_s` for paper claims; it is robust to
  occasional OS scheduling outliers.
- **stdev** — values above ~5% of the median indicate system load interference;
  re-run with the machine otherwise idle.
- **Per-stage percentages** are computed relative to the summed per-tile time
  logged in the debug file, not the total wall-clock time. The remainder
  (pipeline setup, I/O, inter-tile overhead) is not attributed to any stage.
- **n_tiles** — the count of tiles processed in the final timed run. Verify
  it matches the expected tile count for the dataset used.
