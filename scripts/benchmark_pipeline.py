#!/usr/bin/env python3
"""
benchmark_pipeline.py

Measures SlidePrep end-to-end and per-stage processing time for the
SoftwareX paper timing claims (Scenario A / Scenario B).

Usage:
    python scripts/benchmark_pipeline.py config/production.json --repeats 3
    python scripts/benchmark_pipeline.py config/production.json --repeats 3 --cpu-only
    python scripts/benchmark_pipeline.py config/production.json --repeats 3 --both

See docs/BENCHMARKING_GUIDE.md for prerequisites, output format, and how to
interpret results.
"""

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


STEP_COMPLETE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) DEBUG Step (\w+) completed successfully"
)
LOG_TIMESTAMP_FMT = "%Y-%m-%d %H:%M:%S,%f"


def run_once(config_path: str, env: dict, log_path: str) -> float:
    """
    Run main.py once, returning wall-clock duration in seconds.
    `env` should already have CUDA_VISIBLE_DEVICES set appropriately.
    """
    # Remove any stale log from a previous run so per-stage parsing
    # below only sees lines from this run.
    if os.path.exists(log_path):
        os.remove(log_path)

    start = time.perf_counter()
    result = subprocess.run(
        [sys.executable, "main.py", config_path],
        env=env,
        capture_output=True,
        text=True,
    )
    elapsed = time.perf_counter() - start

    if result.returncode != 0:
        print(f"  WARNING: run exited with code {result.returncode}", file=sys.stderr)
        print(result.stderr[-2000:], file=sys.stderr)

    return elapsed


def parse_stage_durations(log_path: str) -> dict:
    """
    Parse the pipeline's own debug log to extract per-stage durations.
    Returns {stage_name: [duration_seconds, ...]} across all tiles processed
    in this run, so the caller can sum or average as needed.

    Relies on log lines of the form:
        2026-06-15 12:57:47,666 DEBUG Step binarization completed successfully
    which already exist in the codebase's logger (src/core/logger.py) —
    no instrumentation added.

    One measurement is intentionally omitted: the very first log event in
    the run has no predecessor timestamp to diff against, so it is silently
    dropped.  Under the current pipeline order that event is always the first
    tile's binarization-complete, which means:

    * ``binarization`` reports n_tiles == number_of_tiles − 1.  Its delta is
      measured as (previous tile's inpainting-complete → binarization-complete),
      which folds in the image-load time; that cost is small enough (~ms) to
      leave the mean usable as a binarization proxy.
    * All other stages report n_tiles == number_of_tiles.

    If the pipeline order ever changes and a different stage becomes first,
    that stage's n_tiles will be one less than the others with no other
    warning.
    """
    if not os.path.exists(log_path):
        return {}

    durations: dict[str, list[float]] = {}
    prev_time = None

    with open(log_path) as f:
        for line in f:
            m = STEP_COMPLETE_RE.match(line)
            if not m:
                continue
            ts_str, stage = m.group(1), m.group(2)
            ts = datetime.strptime(ts_str, LOG_TIMESTAMP_FMT)

            if prev_time is not None:
                delta = (ts - prev_time).total_seconds()
                if delta >= 0:
                    durations.setdefault(stage, []).append(delta)

            prev_time = ts

    return durations


def summarize(durations_list: dict) -> dict:
    """Compute mean/median/stdev per stage across all tiles in a run."""
    summary = {}
    for stage, values in durations_list.items():
        if not values:
            continue
        summary[stage] = {
            "mean_s": round(statistics.mean(values), 4),
            "median_s": round(statistics.median(values), 4),
            "stdev_s": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
            "n_tiles": len(values),
            "total_s": round(sum(values), 4),
        }
    return summary


def run_benchmark(config_path: str, repeats: int, mode: str, log_path: str) -> dict:
    """
    mode: 'cpu' or 'gpu'
    Returns a dict with end-to-end timings and per-stage breakdown
    from the last run (per-stage breakdown is representative; it does
    not need to be re-derived from every repeat since stage costs are
    stable across runs on the same hardware).
    """
    env = os.environ.copy()
    if mode == "cpu":
        env["CUDA_VISIBLE_DEVICES"] = ""
    else:
        env.pop("CUDA_VISIBLE_DEVICES", None)

    print(f"\n=== Benchmarking mode={mode} on {config_path} ===")

    # Warm-up run (model loading, disk cache) — not recorded.
    print("  Warm-up run (not recorded)...")
    run_once(config_path, env, log_path)

    wall_times = []
    for i in range(repeats):
        print(f"  Run {i + 1}/{repeats}...")
        elapsed = run_once(config_path, env, log_path)
        wall_times.append(elapsed)
        print(f"    {elapsed:.1f}s")

    # Per-stage breakdown from the most recent run's debug log.
    stage_durations = parse_stage_durations(log_path)
    stage_summary = summarize(stage_durations)

    return {
        "mode": mode,
        "repeats": repeats,
        "wall_times_s": [round(t, 2) for t in wall_times],
        "median_s": round(statistics.median(wall_times), 2),
        "mean_s": round(statistics.mean(wall_times), 2),
        "stdev_s": round(statistics.stdev(wall_times), 2) if len(wall_times) > 1 else 0.0,
        "stage_breakdown": stage_summary,
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark SlidePrep pipeline timing")
    parser.add_argument("config", help="Path to pipeline config JSON")
    parser.add_argument("--repeats", type=int, default=3,
                        help="Number of timed repeats per mode (default: 3)")
    parser.add_argument("--cpu-only", action="store_true",
                        help="Run CPU-only benchmark (CUDA_VISIBLE_DEVICES='')")
    parser.add_argument("--gpu-only", action="store_true",
                        help="Run GPU-only benchmark (default if no flag given)")
    parser.add_argument("--both", action="store_true",
                        help="Run both CPU and GPU benchmarks for comparison")
    parser.add_argument("--log-path", default=None,
                        help="Path to debug log file. Must match 'log.relative_path' "
                             "in the config, with debug + log_to_file enabled.")
    args = parser.parse_args()

    # Resolve log path: prefer explicit arg, else read from config.
    log_path = args.log_path
    if log_path is None:
        with open(args.config) as f:
            cfg = json.load(f)
        log_file_name = cfg.get("log", {}).get("log_file_name", "pipeline.log")
        output_path = cfg.get("general", {}).get("output_path", "")
        log_path = os.path.join(output_path, log_file_name) if output_path else log_file_name
        if cfg.get("log", {}).get("log_level", "INFO").upper() != "DEBUG":
            print("WARNING: config 'log.log_level' is not DEBUG — per-stage breakdown "
                  "will be empty. Set log_level to DEBUG and log_to_file to true for "
                  "full results.",
                  file=sys.stderr)

    modes = []
    if args.both:
        modes = ["cpu", "gpu"]
    elif args.cpu_only:
        modes = ["cpu"]
    elif args.gpu_only:
        modes = ["gpu"]
    else:
        modes = ["gpu"]  # default: whatever hardware provides

    results = {
        "timestamp": datetime.now().isoformat(),
        "config": args.config,
        "python": sys.version,
        "modes": {},
    }

    for mode in modes:
        results["modes"][mode] = run_benchmark(args.config, args.repeats, mode, log_path)

    # Print summary table
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    for mode, data in results["modes"].items():
        print(f"\n[{mode.upper()}] median={data['median_s']:.1f}s "
              f"mean={data['mean_s']:.1f}s stdev={data['stdev_s']:.1f}s "
              f"(n={data['repeats']} runs)")
        if data["stage_breakdown"]:
            print("  Per-stage breakdown (per-tile, from debug log):")
            total_per_tile = sum(s["total_s"] for s in data["stage_breakdown"].values())
            for stage, s in sorted(data["stage_breakdown"].items(),
                                   key=lambda kv: -kv[1]["total_s"]):
                pct = 100 * s["total_s"] / total_per_tile if total_per_tile else 0
                print(f"    {stage:20s} mean={s['mean_s']:.3f}s/tile  "
                      f"({pct:.1f}% of per-tile time, n={s['n_tiles']} tiles)")
            print("    (binarization n_tiles is one less than other stages: "
                  "the first tile's binarization-complete has no predecessor "
                  "timestamp; its delta also folds in image-load time. "
                  "If pipeline order changes, whichever stage is first will "
                  "show the same n_tiles deficit.)")

    if "cpu" in results["modes"] and "gpu" in results["modes"]:
        cpu_t = results["modes"]["cpu"]["median_s"]
        gpu_t = results["modes"]["gpu"]["median_s"]
        speedup = cpu_t / gpu_t if gpu_t else float("nan")
        reduction_pct = 100 * (1 - gpu_t / cpu_t) if cpu_t else float("nan")
        print(f"\nGPU speedup: {speedup:.2f}x ({reduction_pct:.1f}% time reduction)")
        results["gpu_speedup_factor"] = round(speedup, 2)
        results["gpu_time_reduction_pct"] = round(reduction_pct, 1)

    # Save JSON report
    out_dir = Path("benchmark_results")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_benchmark.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull report saved to {out_path}")


if __name__ == "__main__":
    main()