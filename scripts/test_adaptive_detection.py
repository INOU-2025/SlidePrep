"""CLI script for running and benchmarking adaptive grid-line detection on images."""

import sys
import os
import time
import json
import argparse
import statistics
from pathlib import Path
from datetime import datetime, timezone

# Ensure project root is on Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np
from glob import glob
from src.utils.detection.adaptive_detector import AdaptiveLineDetector
from src.utils.detection.models import DetectionRegion, Orientation
from src.utils.debug.detection_drawer import DetectionDrawer
from src.core.bootstrap import bootstrap
from src.core.app_config_manager import AppConfigManager
from src.core.logger import Logger
from src.core.debugger import Debugger
from typing import Optional


def process_image_adaptive(
    image_path: str,
    output_path: str,
    detector: Optional[AdaptiveLineDetector] = None,
    config_manager: Optional[AppConfigManager] = None,
    logger: Optional[Logger] = None,
    debugger: Optional[Debugger] = None,
) -> dict:
    """
    Process single image with adaptive line detection using logging and debug system.
    
    Args:
        image_path: Path to input image
        output_path: Path for output visualization (can be empty if only using debug system)
        detector: Pre-initialized detector (for cache reuse)
        config_manager: Configuration manager for creating detector if not provided
        
    Returns:
        Dictionary with processing results and timing
        
    Raises:
        ValueError: If detector is None and config_manager is None or missing grid_detection_config
    """
    if logger is None or debugger is None:
        raise ValueError("logger and debugger must be provided")
    
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        logger.error(f"Could not read {image_path}")
        return {}
    
    filename = os.path.basename(image_path)
    logger.info(f"Processing: {filename}")
    
    # Create detector if not provided - REQUIRE valid configuration
    if detector is None:
        if not config_manager:
            raise ValueError("detector is None but no config_manager provided to create detector")
        if not config_manager.grid_detection_config:
            raise ValueError("config_manager.grid_detection_config is None - configuration not loaded properly")
        
        detector = AdaptiveLineDetector(config_manager.grid_detection_config, logger=logger)
    
    start_time = time.time()
    results = detector.detect_lines(image)
    detection_time = time.time() - start_time

    metadata = detector.get_detection_metadata()
    
    logger.info(f"Detection completed in {detection_time:.3f}s")
    total_lines_found = 0
    has_any_detections = False
    
    for orientation, strategy in results['strategies'].items():
        orientation_str = orientation.value if hasattr(orientation, 'value') else str(orientation)
        if strategy:
            contour_dicts = results['detections'][orientation]
            min_area = detector.configs[strategy]["min_contour_area"]
            valid_contours = [item for item in contour_dicts if cv2.contourArea(item['contour']) >= min_area]
            total_lines_found += len(valid_contours)
            if len(valid_contours) > 0:
                has_any_detections = True
            logger.info(f"  {orientation_str}: {len(valid_contours)} lines found using {strategy.value}")
            for item in valid_contours:
                zone_str = item['zone'].value if hasattr(item['zone'], 'value') else str(item['zone'])
                logger.debug(f"    Line zone: {zone_str}")
        else:
            logger.info(f"  {orientation_str}: No lines found")
    
    if 'cache_stats' in results:
        stats = results['cache_stats']
        total_template = stats['template_cache_hits'] + stats['template_cache_misses']
        total_preprocessing = stats['preprocessing_cache_hits'] + stats['preprocessing_cache_misses']
        
        template_rate = f"{stats['template_cache_hits']}/{total_template}" if total_template > 0 else "0/0"
        preprocessing_rate = f"{stats['preprocessing_cache_hits']}/{total_preprocessing}" if total_preprocessing > 0 else "0/0"
        
        logger.debug(f"Cache stats - Template: {template_rate} hits, Preprocessing: {preprocessing_rate} hits")
    
    logger.debug(f"Saving debug image for {filename} - Has detections: {has_any_detections}, Total lines: {total_lines_found}")
    logger.debug(f"Results structure: detections={list(results.get('detections', {}).keys())}, strategies={results.get('strategies', {})}")

    base_name = os.path.splitext(filename)[0]
    extension = os.path.splitext(filename)[1]
    
    current_config = config_manager
    debug_filename = f"{base_name}{extension}"
    
    logger.debug(f"Debug filename with suffix: {debug_filename}")
    
    debugger.save_debug_image(debug_filename, image, results, metadata)
    
    debug_path = os.path.join(debugger._path, debug_filename) if debugger._path else debug_filename
    if os.path.exists(debug_path):
        logger.debug(f"✓ Debug image successfully saved: {debug_path}")
    else:
        logger.warning(f"✗ Debug image NOT saved for {debug_filename}")
        logger.warning(f"  Expected path: {debug_path}")
        logger.warning(f"  Debugger enabled: {debugger._enabled}")
        logger.warning(f"  Drawer available: {debugger._drawer is not None}")
    
    if output_path and output_path.strip():
        if os.path.exists(debug_path):
            import shutil
            shutil.copy2(debug_path, output_path)
        else:
            logger.warning(f"Debug output not found at {debug_path}")
    
    return {
        'filename': filename,
        'detection_time': detection_time,
        'results': results,
        'cache_stats': results.get('cache_stats', {}),
        'total_lines_found': total_lines_found
    }


def compare_performance_configs(
    baseline_config_path: str,
    optimized_config_path: str,
    ext: str = "png",
    test_image_count: Optional[int] = None,
    repeats: int = 3,
    report_path: Optional[str] = None,
    images_path: Optional[str] = None,
) -> dict:
    """Compare grid detection timing between baseline and optimized configurations.

    Runs each configuration ``repeats`` times over the full image set, computing
    median/mean/stdev of total run time per pass. Images are pre-loaded into
    memory so file I/O is excluded from measurements. Each repeat creates a fresh
    detector (cold caches) to simulate real per-batch conditions.

    Args:
        baseline_config_path: Path to baseline configuration (caching disabled).
        optimized_config_path: Path to optimized configuration (caching enabled).
        ext: Image file extension to glob for.
        test_image_count: Cap on number of images to use (None = all).
        repeats: Number of full passes over the image set per config.
        report_path: If given, write JSON results to this path.

    Returns:
        Results dict with timing stats, speedup, and cache hit rates.

    Raises:
        ValueError: If configuration files are missing or image directory is empty.
    """
    for path, label in [
        (baseline_config_path, "Baseline"),
        (optimized_config_path, "Optimized"),
    ]:
        if not os.path.exists(path):
            raise ValueError(f"{label} configuration file not found: {path}")

    baseline_cm = AppConfigManager(baseline_config_path)
    optimized_cm = AppConfigManager(optimized_config_path)

    if not baseline_cm.grid_detection_config:
        raise ValueError(f"grid_detection_config not found in {baseline_config_path}")
    if not optimized_cm.grid_detection_config:
        raise ValueError(f"grid_detection_config not found in {optimized_config_path}")

    test_cfg = baseline_cm.test_config
    input_folder = images_path or (test_cfg.input_path if test_cfg else "")
    if not input_folder:
        raise ValueError(
            "No image path specified. Use --images PATH or set test.input_path "
            f"in {baseline_config_path}"
        )

    # test.max_images acts as the built-in cap; --count overrides it explicitly.
    cap = test_image_count if test_image_count is not None else (
        test_cfg.max_images if test_cfg else None
    )

    image_paths = sorted(glob(os.path.join(input_folder, f"*.{ext}")))
    if not image_paths:
        raise ValueError(f"No {ext} files found in {input_folder}")
    if cap is not None:
        image_paths = image_paths[:min(cap, len(image_paths))]

    # Pre-load images into memory — file I/O must not contribute to timing.
    images = [
        cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        for p in image_paths
    ]
    images = [img for img in images if img is not None]
    if not images:
        raise ValueError(f"No valid images loaded from {input_folder}")

    drawer = DetectionDrawer()

    print()
    print("=" * 60)
    print("CACHE OPTIMIZATION BENCHMARK")
    print("=" * 60)
    print(f"Images:    {len(images)} ({ext}) from {input_folder}")
    print(f"Repeats:   {repeats}")
    print(f"Baseline:  {baseline_config_path}")
    print(f"Optimized: {optimized_config_path}")

    def _time_config(config_path: str, label: str) -> tuple[list[float], dict]:
        container = bootstrap(config_path, drawer=drawer)
        logger = container.resolve("logger")
        gd_config = container.resolve("config").grid_detection_config

        run_times: list[float] = []
        last_detector = None
        print(f"\nRunning {label} ({repeats} repeat{'s' if repeats > 1 else ''})...")
        for i in range(repeats):
            detector = AdaptiveLineDetector(gd_config, logger=logger)
            t0 = time.perf_counter()
            for img in images:
                detector.detect_lines(img)
            elapsed = time.perf_counter() - t0
            run_times.append(elapsed)
            last_detector = detector
            print(f"  repeat {i + 1}/{repeats}: {elapsed:.3f}s", flush=True)

        cache_info = last_detector.get_cache_info() if last_detector else {}
        return run_times, cache_info

    baseline_times, baseline_cache = _time_config(baseline_config_path, "baseline")
    optimized_times, optimized_cache = _time_config(optimized_config_path, "optimized")

    def _stats(times: list[float]) -> dict:
        return {
            "median": statistics.median(times),
            "mean": statistics.mean(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0.0,
            "runs": times,
        }

    b = _stats(baseline_times)
    o = _stats(optimized_times)

    speedup = b["median"] / o["median"] if o["median"] > 0 else float("inf")
    pct_reduction = (
        (b["median"] - o["median"]) / b["median"] * 100 if b["median"] > 0 else 0.0
    )

    def _hit_rate(cache: dict, key: str) -> dict:
        hits = cache.get(f"{key}_cache_hits", 0)
        misses = cache.get(f"{key}_cache_misses", 0)
        total = hits + misses
        return {
            "hits": hits,
            "misses": misses,
            "total": total,
            "rate_pct": hits / total * 100 if total > 0 else 0.0,
        }

    tmpl = _hit_rate(optimized_cache, "template")
    prep = _hit_rate(optimized_cache, "preprocessing")

    baseline_gd = baseline_cm.grid_detection_config
    optimized_gd = optimized_cm.grid_detection_config

    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(
        f"Baseline  (n={repeats}): "
        f"median={b['median']:.3f}s  mean={b['mean']:.3f}s  stdev={b['stdev']:.3f}s"
    )
    print(
        f"Optimized (n={repeats}): "
        f"median={o['median']:.3f}s  mean={o['mean']:.3f}s  stdev={o['stdev']:.3f}s"
    )
    print(f"Speedup: {speedup:.2f}x  ({pct_reduction:.1f}% reduction)")
    print()
    print("Optimization flags (optimized config):")
    print(f"  enable_early_exit:          {optimized_gd.enable_early_exit}")
    print(f"  enable_template_cache:      {optimized_gd.enable_template_cache}")
    print(f"  enable_preprocessing_cache: {optimized_gd.enable_preprocessing_cache}")
    print()
    print("Cache hit rates (optimized, last repeat):")
    print(
        f"  Template:      {tmpl['hits']}/{tmpl['total']}  ({tmpl['rate_pct']:.1f}%)"
    )
    print(
        f"  Preprocessing: {prep['hits']}/{prep['total']}  ({prep['rate_pct']:.1f}%)"
    )
    print("=" * 60)

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "image_count": len(images),
        "repeats": repeats,
        "baseline": {
            "config": baseline_config_path,
            "enable_early_exit": baseline_gd.enable_early_exit,
            "enable_template_cache": baseline_gd.enable_template_cache,
            "enable_preprocessing_cache": baseline_gd.enable_preprocessing_cache,
            **b,
        },
        "optimized": {
            "config": optimized_config_path,
            "enable_early_exit": optimized_gd.enable_early_exit,
            "enable_template_cache": optimized_gd.enable_template_cache,
            "enable_preprocessing_cache": optimized_gd.enable_preprocessing_cache,
            **o,
            "template_hit_rate_pct": tmpl["rate_pct"],
            "preprocessing_hit_rate_pct": prep["rate_pct"],
        },
        "speedup": speedup,
        "pct_reduction": pct_reduction,
    }

    if report_path:
        with open(report_path, "w") as fh:
            json.dump(results, fh, indent=2)
        print(f"\nReport saved to: {report_path}")

    return results


def process_batch_adaptive(config_path: str, ext: str = "png") -> None:
    """
    Process batch of images with adaptive line detection using configuration.
    
    Args:
        config_path: Path to configuration file (required)
        ext: Image file extension
        
    Raises:
        ValueError: If configuration file is missing or doesn't contain required settings
    """
    # Load configuration - fail fast if missing
    if not os.path.exists(config_path):
        raise ValueError(f"Configuration file not found: {config_path}")
    
    config_manager = AppConfigManager(config_path)
    
    if not config_manager.grid_detection_config:
        raise ValueError(f"grid_detection_config not found in {config_path} - check configuration file structure")
    
    input_folder = config_manager.general_config.input_path
    
    if not input_folder:
        raise ValueError(f"input_path not specified in configuration: {config_path}")
    
    drawer = DetectionDrawer()
    
    container = bootstrap(config_path, drawer=drawer)
    logger = container.resolve("logger")
    debugger = container.resolve("debugger")

    logger.info(f"Using configuration from: {config_path}")
    logger.info(f"Input folder: {input_folder}")
    logger.info(f"Debug output will be saved to: {debugger._path}")

    image_paths = glob(os.path.join(input_folder, f"*.{ext}"))
    
    if not image_paths:
        logger.error(f"No {ext} files found in {input_folder}")
        return
    
    logger.info("=" * 60)
    logger.info("BATCH PROCESSING")
    logger.info("=" * 60)
    logger.info(f"Found {len(image_paths)} images to process")
    
    detector = AdaptiveLineDetector(config_manager.grid_detection_config, logger=logger)
    logger.info("Using detector configuration from JSON file")
    
    all_results = []
    total_start_time = time.time()
    
    for i, image_path in enumerate(image_paths, 1):
        filename = os.path.basename(image_path)
        # Debug output will be handled by debugger.save_debug_image()
        # No need for separate output_path since debug system manages this
        
        logger.info(f"[{i}/{len(image_paths)}] Processing {os.path.basename(image_path)}")
        result = process_image_adaptive(image_path, "", detector, config_manager, logger, debugger)  # Empty output_path since debug handles it
        
        if result:
            all_results.append(result)
    
    total_time = time.time() - total_start_time
    
    logger.info("=" * 60)
    logger.info("BATCH PROCESSING SUMMARY")
    logger.info("=" * 60)
    
    if all_results:
        avg_time = sum(r['detection_time'] for r in all_results) / len(all_results)
        total_lines = sum(r['total_lines_found'] for r in all_results)
        
        logger.info(f"Total images processed: {len(all_results)}")
        logger.info(f"Total processing time: {total_time:.3f}s")
        logger.info(f"Average time per image: {avg_time:.3f}s")
        logger.info(f"Total lines detected: {total_lines}")
        logger.info(f"Processing rate: {len(all_results)/total_time:.2f} images/second")
        
        final_cache_info = detector.get_cache_info()
        template_total = final_cache_info['template_cache_hits'] + final_cache_info['template_cache_misses']
        preprocessing_total = final_cache_info['preprocessing_cache_hits'] + final_cache_info['preprocessing_cache_misses']
        
        if template_total > 0:
            template_efficiency = (final_cache_info['template_cache_hits'] / template_total) * 100
            logger.info(f"Template cache efficiency: {template_efficiency:.1f}%")
        
        if preprocessing_total > 0:
            preprocessing_efficiency = (final_cache_info['preprocessing_cache_hits'] / preprocessing_total) * 100
            logger.info(f"Preprocessing cache efficiency: {preprocessing_efficiency:.1f}%")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Adaptive grid detection — testing and cache benchmarking",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    cmp = subparsers.add_parser(
        "compare",
        help="Benchmark cache-optimization speedup between two configs",
    )
    cmp.add_argument(
        "--baseline",
        default="config/test/performance_baseline.json",
        metavar="PATH",
        help="Baseline config path (default: config/test/performance_baseline.json)",
    )
    cmp.add_argument(
        "--optimized",
        default="config/test/performance_optimized.json",
        metavar="PATH",
        help="Optimized config path (default: config/test/performance_optimized.json)",
    )
    cmp.add_argument(
        "--repeats",
        type=int,
        default=3,
        metavar="N",
        help="Full passes over image set per config (default: 3)",
    )
    cmp.add_argument(
        "--report",
        default=None,
        metavar="PATH",
        help="Save JSON results to this path",
    )
    cmp.add_argument(
        "--ext",
        default="png",
        metavar="EXT",
        help="Image file extension (default: png)",
    )
    cmp.add_argument(
        "--images",
        default=None,
        metavar="PATH",
        help="Directory of images to test (overrides general.input_path in configs)",
    )
    cmp.add_argument(
        "--count",
        type=int,
        default=None,
        metavar="N",
        help="Limit number of images used",
    )

    bat = subparsers.add_parser(
        "batch",
        help="Process a batch of images with a single config",
    )
    bat.add_argument(
        "--config",
        default="config/test/grid_detection.json",
        metavar="PATH",
        help="Config path (default: config/test/grid_detection.json)",
    )
    bat.add_argument(
        "--ext",
        default="png",
        metavar="EXT",
        help="Image file extension (default: png)",
    )

    args = parser.parse_args()

    if args.command == "compare":
        compare_performance_configs(
            baseline_config_path=args.baseline,
            optimized_config_path=args.optimized,
            ext=args.ext,
            test_image_count=args.count,
            repeats=args.repeats,
            report_path=args.report,
            images_path=args.images,
        )
    elif args.command == "batch":
        process_batch_adaptive(config_path=args.config, ext=args.ext)