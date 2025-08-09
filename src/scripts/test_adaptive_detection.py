import sys
import os
import time
from pathlib import Path

# Ensure project root is on Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import cv2
import numpy as np
from glob import glob
from src.utils.detection.adaptive_detector import AdaptiveLineDetector
from src.utils.detection.models import DetectionRegion, Orientation
from src.utils.debug.detection_drawer import DetectionDrawer
from src.core.bootstrap import bootstrap, get_logger, get_debugger, get_config
from src.core.app_config_manager import AppConfigManager
from typing import Optional


def process_image_adaptive(image_path: str, output_path: str, detector: Optional[AdaptiveLineDetector] = None, 
                          config_manager: Optional[AppConfigManager] = None) -> dict:
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
    logger = get_logger()
    debugger = get_debugger()
    
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
        
        detector = AdaptiveLineDetector(config_manager.grid_detection_config)
    
    # Time the detection
    start_time = time.time()
    results = detector.detect_lines(image)
    detection_time = time.time() - start_time

    # Get metadata separately
    metadata = detector.get_detection_metadata()
    
    # Log detection summary
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
    
    # Log cache statistics
    if 'cache_stats' in results:
        stats = results['cache_stats']
        total_template = stats['template_cache_hits'] + stats['template_cache_misses']
        total_preprocessing = stats['preprocessing_cache_hits'] + stats['preprocessing_cache_misses']
        
        template_rate = f"{stats['template_cache_hits']}/{total_template}" if total_template > 0 else "0/0"
        preprocessing_rate = f"{stats['preprocessing_cache_hits']}/{total_preprocessing}" if total_preprocessing > 0 else "0/0"
        
        logger.debug(f"Cache stats - Template: {template_rate} hits, Preprocessing: {preprocessing_rate} hits")
    
    # Debug: Log what we're about to save
    logger.debug(f"Saving debug image for {filename} - Has detections: {has_any_detections}, Total lines: {total_lines_found}")
    logger.debug(f"Results structure: detections={list(results.get('detections', {}).keys())}, strategies={results.get('strategies', {})}")

    # Apply output suffix from configuration to debug filename
    base_name = os.path.splitext(filename)[0]
    extension = os.path.splitext(filename)[1]
    
    # Get suffix from current bootstrapped config or fallback to provided config_manager
    current_config = get_config() if config_manager is None else config_manager
    output_suffix = current_config.general_config.output_suffix or ""
    debug_filename = f"{base_name}{output_suffix}{extension}"
    
    logger.debug(f"Debug filename with suffix: {debug_filename}")
    
    # Save debug image with new structure
    debugger.save_debug_image(debug_filename, image, results, metadata)
    
    # Verify the debug image was actually saved
    debug_output_path = os.path.join(debugger._output_dir, debug_filename) if debugger._output_dir else debug_filename
    if os.path.exists(debug_output_path):
        logger.debug(f"✓ Debug image successfully saved: {debug_output_path}")
    else:
        logger.warning(f"✗ Debug image NOT saved for {debug_filename}")
        logger.warning(f"  Expected path: {debug_output_path}")
        logger.warning(f"  Debugger enabled: {debugger._enabled}")
        logger.warning(f"  Drawer available: {debugger._drawer is not None}")
    
    # Only copy to output_path if specified and not empty
    if output_path and output_path.strip():
        if os.path.exists(debug_output_path):
            import shutil
            shutil.copy2(debug_output_path, output_path)
        else:
            logger.warning(f"Debug output not found at {debug_output_path}")
    
    return {
        'filename': filename,
        'detection_time': detection_time,
        'results': results,
        'cache_stats': results.get('cache_stats', {}),
        'total_lines_found': total_lines_found
    }


def compare_performance_configs(baseline_config_path: str, optimized_config_path: str,
                               ext: str = "png", test_image_count:  Optional[int] = None) -> None:
    """
    Compare performance between two different configurations using sequential bootstrap.
    
    Args:
        baseline_config_path: Path to baseline configuration (required)
        optimized_config_path: Path to optimized configuration (required)
        ext: Image file extension
        test_image_count: Number of images to test (default: None for all images)
        
    Raises:
        ValueError: If configuration files are missing or invalid
    """
    # Validate performance test configuration files
    if not os.path.exists(baseline_config_path):
        raise ValueError(f"Baseline configuration file not found: {baseline_config_path}")
    if not os.path.exists(optimized_config_path):
        raise ValueError(f"Optimized configuration file not found: {optimized_config_path}")
    
    # Pre-validate both configurations before starting
    baseline_config_manager = AppConfigManager(baseline_config_path)
    optimized_config_manager = AppConfigManager(optimized_config_path)
    
    if not baseline_config_manager.grid_detection_config:
        raise ValueError(f"grid_detection_config not found in {baseline_config_path}")
    if not optimized_config_manager.grid_detection_config:
        raise ValueError(f"grid_detection_config not found in {optimized_config_path}")
    
    # Extract input path from baseline configuration
    input_folder = baseline_config_manager.general_config.input_path
    
    if not input_folder:
        raise ValueError(f"input_path not specified in baseline configuration: {baseline_config_path}")
    
    # Get test images
    image_paths = glob(os.path.join(input_folder, f"*.{ext}"))
    if not image_paths:
        raise ValueError(f"No {ext} files found in {input_folder}")
    
    # Use all images if no limit specified
    if test_image_count is None:
        test_images = image_paths
    else:
        test_images = image_paths[:min(test_image_count, len(image_paths))]
    
    # Create drawer for both tests
    drawer = DetectionDrawer()
    
    # Initial setup logging
    print("=" * 60)
    print("PERFORMANCE COMPARISON")
    print("=" * 60)
    print(f"Input folder: {input_folder}")
    print(f"Testing {len(test_images)} images")
    print(f"Baseline config: {baseline_config_path}")
    print(f"Optimized config: {optimized_config_path}")
    
    # Test 1: Bootstrap with BASELINE configuration
    bootstrap(baseline_config_path, drawer=drawer)
    logger = get_logger()
    debugger = get_debugger()
    
    logger.info("Testing BASELINE configuration...")
    logger.info(f"Debug output: {debugger._output_dir}")
    
    config_manager = get_config()  # Use the singleton config manager
    detector_baseline = AdaptiveLineDetector(config_manager.grid_detection_config)
    
    times_baseline = []
    for image_path in test_images:
        result = process_image_adaptive(image_path, "", detector_baseline, config_manager)
        if result:
            times_baseline.append(result['detection_time'])
    
    avg_time_baseline = sum(times_baseline) / len(times_baseline) if times_baseline else 0
    baseline_cache_info = detector_baseline.get_cache_info()
    
    # Test 2: Re-bootstrap with OPTIMIZED configuration
    bootstrap(optimized_config_path, drawer=drawer)
    logger = get_logger()
    debugger = get_debugger()
    
    logger.info("Testing OPTIMIZED configuration...")
    logger.info(f"Debug output: {debugger._output_dir}")
    
    config_manager = get_config()  # Use the new singleton config manager
    detector_optimized = AdaptiveLineDetector(config_manager.grid_detection_config)
    
    times_optimized = []
    for image_path in test_images:
        result = process_image_adaptive(image_path, "", detector_optimized, config_manager)
        if result:
            times_optimized.append(result['detection_time'])
    
    avg_time_optimized = sum(times_optimized) / len(times_optimized) if times_optimized else 0
    optimized_cache_info = detector_optimized.get_cache_info()
    
    # Log performance comparison
    logger.info("=" * 60)
    logger.info("PERFORMANCE RESULTS")
    logger.info("=" * 60)
    logger.info(f"Baseline configuration:  {avg_time_baseline:.3f}s average")
    logger.info(f"Optimized configuration: {avg_time_optimized:.3f}s average")
    if avg_time_baseline > 0:
        speedup = avg_time_baseline / avg_time_optimized if avg_time_optimized > 0 else float('inf')
        improvement = ((avg_time_baseline - avg_time_optimized) / avg_time_baseline) * 100
        logger.info(f"Speedup: {speedup:.2f}x ({improvement:.1f}% faster)")
    
    # Log optimization settings comparison
    baseline_grid = baseline_config_manager.grid_detection_config
    optimized_grid = optimized_config_manager.grid_detection_config
    
    logger.info("Configuration Comparison:")
    logger.info(f"  Early Exit - Baseline: {baseline_grid.enable_early_exit}, Optimized: {optimized_grid.enable_early_exit}")
    logger.info(f"  Template Cache - Baseline: {baseline_grid.enable_template_cache}, Optimized: {optimized_grid.enable_template_cache}")
    logger.info(f"  Preprocessing Cache - Baseline: {baseline_grid.enable_preprocessing_cache}, Optimized: {optimized_grid.enable_preprocessing_cache}")
    
    # Log cache statistics for both configurations
    logger.info("Cache Statistics Comparison:")
    logger.info(f"  Baseline - Template cache size: {baseline_cache_info['template_cache_size']} entries")
    logger.info(f"  Optimized - Template cache size: {optimized_cache_info['template_cache_size']} entries")
    
    baseline_template_total = baseline_cache_info['template_cache_hits'] + baseline_cache_info['template_cache_misses']
    optimized_template_total = optimized_cache_info['template_cache_hits'] + optimized_cache_info['template_cache_misses']
    
    if baseline_template_total > 0:
        baseline_efficiency = (baseline_cache_info['template_cache_hits'] / baseline_template_total) * 100
        logger.info(f"  Baseline template cache efficiency: {baseline_efficiency:.1f}%")
    
    if optimized_template_total > 0:
        optimized_efficiency = (optimized_cache_info['template_cache_hits'] / optimized_template_total) * 100
        logger.info(f"  Optimized template cache efficiency: {optimized_efficiency:.1f}%")
    
    baseline_preprocessing_total = baseline_cache_info['preprocessing_cache_hits'] + baseline_cache_info['preprocessing_cache_misses']
    optimized_preprocessing_total = optimized_cache_info['preprocessing_cache_hits'] + optimized_cache_info['preprocessing_cache_misses']
    
    if baseline_preprocessing_total > 0:
        baseline_preprocessing_efficiency = (baseline_cache_info['preprocessing_cache_hits'] / baseline_preprocessing_total) * 100
        logger.info(f"  Baseline preprocessing cache efficiency: {baseline_preprocessing_efficiency:.1f}%")
    
    if optimized_preprocessing_total > 0:
        optimized_preprocessing_efficiency = (optimized_cache_info['preprocessing_cache_hits'] / optimized_preprocessing_total) * 100
        logger.info(f"  Optimized preprocessing cache efficiency: {optimized_preprocessing_efficiency:.1f}%")


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
    
    # Extract input path from configuration
    input_folder = config_manager.general_config.input_path
    
    if not input_folder:
        raise ValueError(f"input_path not specified in configuration: {config_path}")
    
    # Create adaptive detection drawer (strategy overlay removed)
    drawer = DetectionDrawer()
    
    # Bootstrap the system
    bootstrap(config_path, drawer=drawer)
    logger = get_logger()
    debugger = get_debugger()
    
    logger.info(f"Using configuration from: {config_path}")
    logger.info(f"Input folder: {input_folder}")
    logger.info(f"Debug output will be saved to: {debugger._output_dir}")
    
    image_paths = glob(os.path.join(input_folder, f"*.{ext}"))
    
    if not image_paths:
        logger.error(f"No {ext} files found in {input_folder}")
        return
    
    logger.info("=" * 60)
    logger.info("BATCH PROCESSING")
    logger.info("=" * 60)
    logger.info(f"Found {len(image_paths)} images to process")
    
    # Process all images with the configuration
    detector = AdaptiveLineDetector(config_manager.grid_detection_config)
    logger.info("Using detector configuration from JSON file")
    
    all_results = []
    total_start_time = time.time()
    
    for i, image_path in enumerate(image_paths, 1):
        filename = os.path.basename(image_path)
        # Debug output will be handled by debugger.save_debug_image()
        # No need for separate output_path since debug system manages this
        
        logger.info(f"[{i}/{len(image_paths)}] Processing {os.path.basename(image_path)}")
        result = process_image_adaptive(image_path, "", detector, config_manager)  # Empty output_path since debug handles it
        
        if result:
            all_results.append(result)
    
    total_time = time.time() - total_start_time
    
    # Final summary
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
        
        # Cache efficiency summary
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
    # Example usage with explicit configuration paths
    
    # Option 1: Compare performance between two configurations
    '''
    compare_performance_configs(
         baseline_config_path="config/test/performance_baseline.json",
         optimized_config_path="config/test/performance_optimized.json"
    )
    '''
    # Option 2: Process batch with test configuration
    process_batch_adaptive(config_path="config/test/grid_detection.json")