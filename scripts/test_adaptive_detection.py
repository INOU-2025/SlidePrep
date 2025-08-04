import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import cv2
import numpy as np
from glob import glob
from utils.detection.template_matching import AdaptiveLineDetector


def process_image_adaptive(image_path: str, output_path: str, verbose: bool = True) -> None:
    """
    Process single image with adaptive line detection.
    
    Args:
        image_path: Path to input image
        output_path: Path for output visualization
        verbose: Whether to print detection strategy information
    """
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        print(f"Could not read {image_path}")
        return
    
    print(f"\nProcessing: {os.path.basename(image_path)}")
    
    # Create adaptive detector
    detector = AdaptiveLineDetector(min_contour_area=100, verbose=verbose)
    
    # Detect lines
    results = detector.detect_lines(image)
    
    # Create visualization
    visualization = detector.create_visualization(image, results)
    
    # Save result
    cv2.imwrite(output_path, visualization)
    
    # Print summary
    print(f"Detection summary:")
    for orientation, strategy in results['strategies'].items():
        if strategy:
            mask, contours = results['detections'][orientation]
            valid_contours = [c for c in contours if cv2.contourArea(c) >= 100]
            print(f"  {orientation}: {len(valid_contours)} lines found using {strategy.value}")
        else:
            print(f"  {orientation}: No lines found")


def process_batch_adaptive(input_folder: str, output_folder: str, ext: str = "png") -> None:
    """
    Process batch of images with adaptive line detection.
    
    Args:
        input_folder: Input directory path
        output_folder: Output directory path
        ext: Image file extension
    """
    os.makedirs(output_folder, exist_ok=True)
    image_paths = glob(os.path.join(input_folder, f"*.{ext}"))
    
    for image_path in image_paths:
        filename = os.path.basename(image_path)
        output_path = os.path.join(output_folder, filename)
        process_image_adaptive(image_path, output_path, verbose=True)


if __name__ == "__main__":
    # Example usage with adaptive detection
    process_batch_adaptive(
        "/Users/irconde/Downloads/V2_170225_exp250225/bin-select",         # input folder
        "/Users/irconde/Downloads/V2_170225_exp250225/adaptive_detection"  # output folder
    )