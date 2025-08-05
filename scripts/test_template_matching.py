import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import cv2
import numpy as np
from glob import glob
from utils.detection.adaptive_detector import AdaptiveLineDetector
from utils.detection.models import DetectionStrategy
from utils.debug.adaptive_detection_drawer import AdaptiveDetectionDrawer


def create_visualization(image: np.ndarray, results: dict, detector: AdaptiveLineDetector) -> np.ndarray:
    """
    Create visualization using the adaptive detection drawer.
    
    Args:
        image: Input grayscale image
        results: Detection results from AdaptiveLineDetector.detect_lines()
        detector: The detector instance (for metadata)
    
    Returns:
        Visualization image
    """
    drawer = AdaptiveDetectionDrawer(
        show_strategy_info=True,
        show_cache_stats=True,
        show_border_zones=True
    )
    
    metadata = {'detector': detector}
    visualization = drawer.draw(image, results, metadata)
    
    return visualization if visualization is not None else cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)


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
        Dictionary with processing results
    """
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        print(f"Could not read {image_path}")
        return {}
    
    filename = os.path.basename(image_path)
    if verbose:
        print(f"Processing: {filename}")
    
    # Create detector if not provided
    if detector is None:
        detector = AdaptiveLineDetector(
            min_contour_area=100, 
            verbose=verbose
        )
    
    # Detect lines
    results = detector.detect_lines(image)
    
    # Create visualization using the drawer
    visualization = create_visualization(image, results, detector)
    
    # Save result
    cv2.imwrite(output_path, visualization)
    
    # Extract detection counts
    detections = results['detections']
    horizontal_count = 0
    vertical_count = 0
    
    if 'horizontal' in detections:
        mask, contours = detections['horizontal']
        horizontal_count = len([c for c in contours if cv2.contourArea(c) >= detector.min_contour_area])
    
    if 'vertical' in detections:
        mask, contours = detections['vertical']
        vertical_count = len([c for c in contours if cv2.contourArea(c) >= detector.min_contour_area])
    
    # Print summary
    if verbose:
        strategies = results['strategies']
        print(f"  Results: {horizontal_count} horizontal, {vertical_count} vertical lines")
        for orientation, strategy in strategies.items():
            if strategy:
                print(f"    {orientation}: found using {strategy.value}")
            else:
                print(f"    {orientation}: not found")
    
    return {
        'filename': filename,
        'horizontal_count': horizontal_count,
        'vertical_count': vertical_count,
        'total_count': horizontal_count + vertical_count,
        'strategies': results['strategies'],
        'success': True
    }


def process_batch_adaptive(input_folder: str, output_folder: str, ext: str = "png", 
                          detector_config: dict = None, reuse_detector: bool = True) -> None:
    """
    Process batch of images with adaptive line detection.
    
    Args:
        input_folder: Input directory path
        output_folder: Output directory path
        ext: Image file extension
        detector_config: Configuration for AdaptiveLineDetector
        reuse_detector: Whether to reuse detector instance for better caching
    """
    os.makedirs(output_folder, exist_ok=True)
    image_paths = glob(os.path.join(input_folder, f"*.{ext}"))
    
    if not image_paths:
        print(f"No {ext} files found in {input_folder}")
        return
    
    print(f"Found {len(image_paths)} images to process")
    
    # Create detector with configuration
    config = detector_config or DEFAULT_ADAPTIVE_CONFIG
    detector = AdaptiveLineDetector(**config) if reuse_detector else None
    
    all_results = []
    
    for i, image_path in enumerate(image_paths, 1):
        filename = os.path.basename(image_path)
        output_path = os.path.join(output_folder, filename)
        
        print(f"[{i}/{len(image_paths)}] Processing {filename}")
        
        # Use shared detector for caching benefits, or create new one each time
        current_detector = detector if reuse_detector else AdaptiveLineDetector(**config)
        
        result = process_image_adaptive(
            image_path, 
            output_path, 
            detector=current_detector, 
            verbose=True
        )
        
        if result:
            all_results.append(result)
    
    # Print batch summary
    if all_results:
        total_lines = sum(r['total_count'] for r in all_results)
        successful_images = len([r for r in all_results if r['success']])
        
        print(f"\nBatch Summary:")
        print(f"  Images processed: {successful_images}/{len(image_paths)}")
        print(f"  Total lines detected: {total_lines}")
        print(f"  Average lines per image: {total_lines/successful_images:.1f}")
        
        # Strategy usage summary
        strategy_usage = {}
        for result in all_results:
            for orientation, strategy in result['strategies'].items():
                if strategy:
                    key = f"{orientation}_{strategy.value}"
                    strategy_usage[key] = strategy_usage.get(key, 0) + 1
        
        if strategy_usage:
            print(f"  Strategy usage:")
            for strategy_combo, count in strategy_usage.items():
                print(f"    {strategy_combo}: {count} images")
        
        # Cache performance if available
        if reuse_detector and detector:
            if detector.template_cache:
                template_stats = detector.template_cache.get_stats()
                print(f"  Template cache: {template_stats['hits']}/{template_stats['hits'] + template_stats['misses']} hits")
            
            if detector.preprocessing_cache:
                preprocessing_stats = detector.preprocessing_cache.get_stats()
                print(f"  Preprocessing cache: {preprocessing_stats['hits']}/{preprocessing_stats['hits'] + preprocessing_stats['misses']} hits")


def test_different_configurations(input_folder: str, output_base: str) -> None:
    """
    Test different detector configurations on the same set of images.
    
    Args:
        input_folder: Input directory path
        output_base: Base output directory path
    """
    configurations = {
        'optimized': {
            'min_contour_area': 100,
            'verbose': False,
            'enable_early_exit': True,
            'enable_template_cache': True,
            'enable_preprocessing_cache': True,
            'cache_max_size': 50
        },
        'conservative': {
            'min_contour_area': 200,
            'verbose': False,
            'enable_early_exit': True,
            'enable_template_cache': True,
            'enable_preprocessing_cache': True,
            'cache_max_size': 50
        },
        'no_cache': {
            'min_contour_area': 100,
            'verbose': False,
            'enable_early_exit': True,
            'enable_template_cache': False,
            'enable_preprocessing_cache': False,
            'cache_max_size': 50
        }
    }
    
    for config_name, config in configurations.items():
        print(f"\n{'='*60}")
        print(f"Testing configuration: {config_name.upper()}")
        print(f"{'='*60}")
        
        output_folder = os.path.join(output_base, config_name)
        process_batch_adaptive(
            input_folder,
            output_folder,
            detector_config=config,
            reuse_detector=True
        )


# Configuration presets
DEFAULT_ADAPTIVE_CONFIG = {
    'min_contour_area': 100,
    'verbose': True,
    'enable_early_exit': True,
    'enable_template_cache': True,
    'enable_preprocessing_cache': True,
    'cache_max_size': 50
}

FAST_CONFIG = {
    'min_contour_area': 100,
    'verbose': False,
    'enable_early_exit': True,
    'enable_template_cache': True,
    'enable_preprocessing_cache': True,
    'cache_max_size': 100
}

CONSERVATIVE_CONFIG = {
    'min_contour_area': 200,
    'verbose': True,
    'enable_early_exit': False,  # Process all strategies for thorough detection
    'enable_template_cache': True,
    'enable_preprocessing_cache': True,
    'cache_max_size': 50
}


if __name__ == "__main__":
    # Example usage with adaptive detection
    
    # Option 1: Basic batch processing with default configuration
    process_batch_adaptive(
        "/Users/irconde/Downloads/V2_170225_exp250225/bin-select",         # input folder
        "/Users/irconde/Downloads/V2_170225_exp250225/adaptive_detection", # output folder
        detector_config=DEFAULT_ADAPTIVE_CONFIG
    )
    
    # Option 2: Test different configurations for comparison
    # test_different_configurations(
    #     "/Users/irconde/Downloads/V2_170225_exp250225/bin-select",
    #     "/Users/irconde/Downloads/V2_170225_exp250225/config_comparison"
    # )
    
    # Option 3: Fast processing with optimized settings
    # process_batch_adaptive(
    #     "/Users/irconde/Downloads/V2_170225_exp250225/bin-select",
    #     "/Users/irconde/Downloads/V2_170225_exp250225/fast_detection",
    #     detector_config=FAST_CONFIG
    # )
