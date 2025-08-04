import sys
import os
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import cv2
import numpy as np
from glob import glob
from utils.detection.adaptive_detector import AdaptiveLineDetector
from utils.debug.adaptive_detection_drawer import AdaptiveDetectionDrawer
from core.bootstrap import bootstrap, get_logger, get_debugger


def process_image_adaptive(image_path: str, output_path: str, detector: AdaptiveLineDetector = None, 
                          verbose: bool = True) -> dict:
    """
    Process single image with adaptive line detection using logging and debug system.
    
    Args:
        image_path: Path to input image
        output_path: Path for output visualization
        detector: Pre-initialized detector (for cache reuse)
        verbose: Whether to print detection strategy information
        
    Returns:
        Dictionary with processing results and timing
    """
    logger = get_logger()
    debugger = get_debugger()
    
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        logger.error(f"Could not read {image_path}")
        return {}
    
    filename = os.path.basename(image_path)
    logger.info(f"Processing: {filename}")
    
    # Create detector if not provided
    if detector is None:
        detector = AdaptiveLineDetector(
            min_contour_area=100, 
            verbose=verbose,
            enable_early_exit=True,
            enable_template_cache=True,
            enable_preprocessing_cache=True
        )
    
    # Time the detection
    start_time = time.time()
    results = detector.detect_lines(image)
    detection_time = time.time() - start_time
    
    # Log detection summary
    logger.info(f"Detection completed in {detection_time:.3f}s")
    for orientation, strategy in results['strategies'].items():
        if strategy:
            mask, contours = results['detections'][orientation]
            valid_contours = [c for c in contours if cv2.contourArea(c) >= detector.min_contour_area]
            logger.info(f"  {orientation}: {len(valid_contours)} lines found using {strategy.value}")
        else:
            logger.info(f"  {orientation}: No lines found")
    
    # Log cache statistics
    if 'cache_stats' in results:
        stats = results['cache_stats']
        total_template = stats['template_cache_hits'] + stats['template_cache_misses']
        total_preprocessing = stats['preprocessing_cache_hits'] + stats['preprocessing_cache_misses']
        
        template_rate = f"{stats['template_cache_hits']}/{total_template}" if total_template > 0 else "0/0"
        preprocessing_rate = f"{stats['preprocessing_cache_hits']}/{total_preprocessing}" if total_preprocessing > 0 else "0/0"
        
        logger.debug(f"Cache stats - Template: {template_rate} hits, Preprocessing: {preprocessing_rate} hits")
    
    # Create visualization using debug system
    metadata = {
        'detector': detector,
        'timing': detection_time,
        'filename': filename
    }
    debugger.save_debug_image(filename, image, results, metadata)
    
    # Also save to specified output path by copying the debug output
    debug_output = os.path.join(debugger._output_dir, filename) if debugger._output_dir else filename
    if os.path.exists(debug_output):
        import shutil
        shutil.copy2(debug_output, output_path)
    else:
        logger.warning(f"Debug output not found at {debug_output}")
    
    return {
        'filename': filename,
        'detection_time': detection_time,
        'results': results,
        'cache_stats': results.get('cache_stats', {}),
        'total_lines_found': sum(len([c for c in results['detections'][orient][1] 
                                    if cv2.contourArea(c) >= detector.min_contour_area]) 
                                for orient in results['detections'])
    }


def process_batch_adaptive(input_folder: str, output_folder: str, ext: str = "png", 
                          test_performance: bool = True, config_path: str = None) -> None:
    """
    Process batch of images with adaptive line detection using logging system.
    
    Args:
        input_folder: Input directory path
        output_folder: Output directory path
        ext: Image file extension
        test_performance: Whether to run performance comparison tests
        config_path: Path to configuration file (defaults to development config)
    """
    # Initialize the debug/logging system
    if config_path is None:
        config_path = str(Path(__file__).parent.parent / "config" / "development.json")
    
    # Create adaptive detection drawer
    drawer = AdaptiveDetectionDrawer(
        show_strategy_info=True,
        show_cache_stats=True,
        show_border_zones=True
    )
    
    # Bootstrap the system
    bootstrap(config_path, drawer=drawer)
    logger = get_logger()
    debugger = get_debugger()
    
    os.makedirs(output_folder, exist_ok=True)
    image_paths = glob(os.path.join(input_folder, f"*.{ext}"))
    
    if not image_paths:
        logger.error(f"No {ext} files found in {input_folder}")
        return
    
    logger.info(f"Found {len(image_paths)} images to process")
    
    if test_performance and len(image_paths) > 1:
        # Performance comparison: with and without optimizations
        logger.info("=" * 60)
        logger.info("PERFORMANCE COMPARISON")
        logger.info("=" * 60)
        
        # Test 1: Without optimizations
        logger.info("Testing WITHOUT optimizations (first 3 images)...")
        detector_no_opt = AdaptiveLineDetector(
            min_contour_area=100,
            verbose=False,
            enable_early_exit=False,
            enable_template_cache=False,
            enable_preprocessing_cache=False
        )
        
        times_no_opt = []
        test_images = image_paths[:min(3, len(image_paths))]
        
        for image_path in test_images:
            filename = os.path.basename(image_path)
            output_path = os.path.join(output_folder, f"no_opt_{filename}")
            result = process_image_adaptive(image_path, output_path, detector_no_opt, verbose=False)
            if result:
                times_no_opt.append(result['detection_time'])
        
        avg_time_no_opt = sum(times_no_opt) / len(times_no_opt) if times_no_opt else 0
        
        # Test 2: With optimizations
        logger.info("Testing WITH optimizations (same images)...")
        detector_opt = AdaptiveLineDetector(
            min_contour_area=100,
            verbose=False,
            enable_early_exit=True,
            enable_template_cache=True,
            enable_preprocessing_cache=True
        )
        
        times_opt = []
        
        for image_path in test_images:
            filename = os.path.basename(image_path)
            output_path = os.path.join(output_folder, f"opt_{filename}")
            result = process_image_adaptive(image_path, output_path, detector_opt, verbose=False)
            if result:
                times_opt.append(result['detection_time'])
        
        avg_time_opt = sum(times_opt) / len(times_opt) if times_opt else 0
        
        # Log performance comparison
        logger.info("Performance Results:")
        logger.info(f"  Without optimizations: {avg_time_no_opt:.3f}s average")
        logger.info(f"  With optimizations:    {avg_time_opt:.3f}s average")
        if avg_time_no_opt > 0:
            speedup = avg_time_no_opt / avg_time_opt if avg_time_opt > 0 else float('inf')
            improvement = ((avg_time_no_opt - avg_time_opt) / avg_time_no_opt) * 100
            logger.info(f"  Speedup: {speedup:.2f}x ({improvement:.1f}% faster)")
        
        # Log cache statistics
        cache_info = detector_opt.get_cache_info()
        logger.info("Final Cache Statistics:")
        logger.info(f"  Template cache size: {cache_info['template_cache_size']} entries")
        logger.info(f"  Preprocessing cache size: {cache_info['preprocessing_cache_size']} entries")
        
        template_total = cache_info['template_cache_hits'] + cache_info['template_cache_misses']
        preprocessing_total = cache_info['preprocessing_cache_hits'] + cache_info['preprocessing_cache_misses']
        
        if template_total > 0:
            template_efficiency = (cache_info['template_cache_hits'] / template_total) * 100
            logger.info(f"  Template cache efficiency: {template_efficiency:.1f}%")
        
        if preprocessing_total > 0:
            preprocessing_efficiency = (cache_info['preprocessing_cache_hits'] / preprocessing_total) * 100
            logger.info(f"  Preprocessing cache efficiency: {preprocessing_efficiency:.1f}%")
    
    logger.info("=" * 60)
    logger.info("PROCESSING ALL IMAGES WITH OPTIMIZATIONS")
    logger.info("=" * 60)
    
    # Process all images with optimizations and debug system
    detector = AdaptiveLineDetector(
        min_contour_area=100,
        verbose=True,
        enable_early_exit=True,
        enable_template_cache=True,
        enable_preprocessing_cache=True
    )
    
    all_results = []
    total_start_time = time.time()
    
    for i, image_path in enumerate(image_paths, 1):
        filename = os.path.basename(image_path)
        output_path = os.path.join(output_folder, filename)
        
        logger.info(f"[{i}/{len(image_paths)}] Processing {filename}")
        result = process_image_adaptive(image_path, output_path, detector, verbose=True)
        
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


def test_single_image(image_path: str, output_dir: str = None, config_path: str = None) -> None:
    """
    Test adaptive detection on a single image with debug system.
    
    Args:
        image_path: Path to test image
        output_dir: Output directory (defaults to same as input)
        config_path: Path to configuration file
    """
    if not os.path.exists(image_path):
        print(f"Image not found: {image_path}")
        return
    
    if output_dir is None:
        output_dir = os.path.dirname(image_path)
    
    if config_path is None:
        config_path = str(Path(__file__).parent.parent / "config" / "development.json")
    
    # Initialize debug system
    drawer = AdaptiveDetectionDrawer(
        show_strategy_info=True,
        show_cache_stats=True,
        show_border_zones=True
    )
    bootstrap(config_path, drawer=drawer)
    logger = get_logger()
    
    os.makedirs(output_dir, exist_ok=True)
    
    filename = os.path.splitext(os.path.basename(image_path))[0]
    output_path = os.path.join(output_dir, f"{filename}_adaptive_result.png")
    
    logger.info("Testing Adaptive Line Detection on Single Image")
    logger.info("=" * 50)
    
    # Test with all optimization features
    detector = AdaptiveLineDetector(
        min_contour_area=100,
        verbose=True,
        enable_early_exit=True,
        enable_template_cache=True,
        enable_preprocessing_cache=True
    )
    
    result = process_image_adaptive(image_path, output_path, detector, verbose=True)
    
    if result:
        logger.info(f"Result saved to: {output_path}")
        cache_info = detector.get_cache_info()
        logger.debug(f"Final detector state: {cache_info}")


if __name__ == "__main__":
    # Example usage with logging and debug system
    
    # Option 1: Process batch with performance comparison and debug system
    process_batch_adaptive(
        "/Users/irconde/Downloads/V2_170225_exp250225/bin-select",         # input folder
        "/Users/irconde/Downloads/V2_170225_exp250225/adaptive_detection", # output folder
        test_performance=True  # Enable performance comparison
    )
    
    # Option 2: Test single image with debug system
    # test_single_image("/path/to/single/image.png", "/path/to/output/directory")