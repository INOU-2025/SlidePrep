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
from utils.detection.template_matching import AdaptiveLineDetector


def process_image_adaptive(image_path: str, output_path: str, detector: AdaptiveLineDetector = None, 
                          verbose: bool = True) -> dict:
    """
    Process single image with adaptive line detection.
    
    Args:
        image_path: Path to input image
        output_path: Path for output visualization
        detector: Pre-initialized detector (for cache reuse)
        verbose: Whether to print detection strategy information
        
    Returns:
        Dictionary with processing results and timing
    """
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        print(f"Could not read {image_path}")
        return {}
    
    print(f"\nProcessing: {os.path.basename(image_path)}")
    
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
    
    # Create visualization
    visualization = detector.create_visualization(image, results)
    
    # Save result
    cv2.imwrite(output_path, visualization)
    
    # Print summary
    print(f"Detection summary (took {detection_time:.3f}s):")
    for orientation, strategy in results['strategies'].items():
        if strategy:
            mask, contours = results['detections'][orientation]
            valid_contours = [c for c in contours if cv2.contourArea(c) >= 100]
            print(f"  {orientation}: {len(valid_contours)} lines found using {strategy.value}")
        else:
            print(f"  {orientation}: No lines found")
    
    # Print cache statistics if available
    if 'cache_stats' in results:
        stats = results['cache_stats']
        print(f"Cache stats - Template: {stats['template_hits']}/{stats['template_hits'] + stats['template_misses']} hits, "
              f"Preprocessing: {stats['preprocessing_hits']}/{stats['preprocessing_hits'] + stats['preprocessing_misses']} hits")
    
    return {
        'filename': os.path.basename(image_path),
        'detection_time': detection_time,
        'results': results,
        'cache_stats': results.get('cache_stats', {}),
        'total_lines_found': sum(len([c for c in results['detections'][orient][1] if cv2.contourArea(c) >= 100]) 
                                for orient in results['detections'])
    }


def process_batch_adaptive(input_folder: str, output_folder: str, ext: str = "png", 
                          test_performance: bool = True) -> None:
    """
    Process batch of images with adaptive line detection.
    
    Args:
        input_folder: Input directory path
        output_folder: Output directory path
        ext: Image file extension
        test_performance: Whether to run performance comparison tests
    """
    os.makedirs(output_folder, exist_ok=True)
    image_paths = glob(os.path.join(input_folder, f"*.{ext}"))
    
    if not image_paths:
        print(f"No {ext} files found in {input_folder}")
        return
    
    print(f"Found {len(image_paths)} images to process")
    
    if test_performance and len(image_paths) > 1:
        # Performance comparison: with and without optimizations
        print("\n" + "="*60)
        print("PERFORMANCE COMPARISON")
        print("="*60)
        
        # Test 1: Without optimizations
        print("\n1. Testing WITHOUT optimizations (first 3 images)...")
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
        
        # Test 2: With optimizations (reuse detector for caching benefits)
        print("\n2. Testing WITH optimizations (same images)...")
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
        
        # Print performance comparison
        print(f"\nPerformance Results:")
        print(f"  Without optimizations: {avg_time_no_opt:.3f}s average")
        print(f"  With optimizations:    {avg_time_opt:.3f}s average")
        if avg_time_no_opt > 0:
            speedup = avg_time_no_opt / avg_time_opt if avg_time_opt > 0 else float('inf')
            improvement = ((avg_time_no_opt - avg_time_opt) / avg_time_no_opt) * 100
            print(f"  Speedup: {speedup:.2f}x ({improvement:.1f}% faster)")
        
        # Show cache statistics
        cache_info = detector_opt.get_cache_info()
        print(f"\nFinal Cache Statistics:")
        print(f"  Template cache size: {cache_info['template_cache_size']} entries")
        print(f"  Preprocessing cache size: {cache_info['preprocessing_cache_size']} entries")
        print(f"  Template cache efficiency: {cache_info['template_cache_hits']}/{cache_info['template_cache_hits'] + cache_info['template_cache_misses']} hits")
        print(f"  Preprocessing cache efficiency: {cache_info['preprocessing_cache_hits']}/{cache_info['preprocessing_cache_hits'] + cache_info['preprocessing_cache_misses']} hits")
    
    print("\n" + "="*60)
    print("PROCESSING ALL IMAGES WITH OPTIMIZATIONS")
    print("="*60)
    
    # Process all images with optimizations
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
        
        print(f"\n[{i}/{len(image_paths)}] Processing {filename}")
        result = process_image_adaptive(image_path, output_path, detector, verbose=True)
        
        if result:
            all_results.append(result)
    
    total_time = time.time() - total_start_time
    
    # Final summary
    print("\n" + "="*60)
    print("BATCH PROCESSING SUMMARY")
    print("="*60)
    
    if all_results:
        avg_time = sum(r['detection_time'] for r in all_results) / len(all_results)
        total_lines = sum(r['total_lines_found'] for r in all_results)
        
        print(f"Total images processed: {len(all_results)}")
        print(f"Total processing time: {total_time:.3f}s")
        print(f"Average time per image: {avg_time:.3f}s")
        print(f"Total lines detected: {total_lines}")
        print(f"Processing rate: {len(all_results)/total_time:.2f} images/second")
        
        # Cache efficiency summary
        final_cache_info = detector.get_cache_info()
        template_total = final_cache_info['template_cache_hits'] + final_cache_info['template_cache_misses']
        preprocessing_total = final_cache_info['preprocessing_cache_hits'] + final_cache_info['preprocessing_cache_misses']
        
        if template_total > 0:
            template_efficiency = (final_cache_info['template_cache_hits'] / template_total) * 100
            print(f"Template cache efficiency: {template_efficiency:.1f}%")
        
        if preprocessing_total > 0:
            preprocessing_efficiency = (final_cache_info['preprocessing_cache_hits'] / preprocessing_total) * 100
            print(f"Preprocessing cache efficiency: {preprocessing_efficiency:.1f}%")


def test_single_image(image_path: str, output_dir: str = None) -> None:
    """
    Test adaptive detection on a single image with detailed output.
    
    Args:
        image_path: Path to test image
        output_dir: Output directory (defaults to same as input)
    """
    if not os.path.exists(image_path):
        print(f"Image not found: {image_path}")
        return
    
    if output_dir is None:
        output_dir = os.path.dirname(image_path)
    
    os.makedirs(output_dir, exist_ok=True)
    
    filename = os.path.splitext(os.path.basename(image_path))[0]
    output_path = os.path.join(output_dir, f"{filename}_adaptive_result.png")
    
    print("Testing Adaptive Line Detection on Single Image")
    print("=" * 50)
    
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
        print(f"\nResult saved to: {output_path}")
        cache_info = detector.get_cache_info()
        print(f"Final detector state: {cache_info}")


if __name__ == "__main__":
    # Example usage with adaptive detection and performance testing
    
    # Option 1: Process batch with performance comparison
    process_batch_adaptive(
        "/Users/irconde/Downloads/V2_170225_exp250225/bin-select",         # input folder
        "/Users/irconde/Downloads/V2_170225_exp250225/adaptive_detection", # output folder
        test_performance=True  # Enable performance comparison
    )
    
    # Option 2: Test single image
    # test_single_image("/path/to/single/image.png", "/path/to/output/directory")