import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import cv2
import numpy as np
from glob import glob
from utils.detection.template_matching import TemplateLineDetector, GeneralLineDetector


def process_image(image_path: str, output_path: str, use_general: bool = False, **kwargs) -> None:
    """
    Process single image for line detection.
    
    Args:
        image_path: Path to input image
        output_path: Path for output visualization
        use_general: Whether to use GeneralLineDetector (no border restrictions)
        **kwargs: Parameters passed to detector
    """
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        print(f"Could not read {image_path}")
        return
    
    # Create appropriate detector
    if use_general:
        detector = GeneralLineDetector(**kwargs)
    else:
        detector = TemplateLineDetector(**kwargs)
    
    # Detect lines
    h_mask, v_mask, h_contours, v_contours = detector.detect_lines(image)
    
    # Create visualization
    result = detector.create_visualization(image, h_contours, v_contours)
    
    # Save result
    cv2.imwrite(output_path, result)


def process_batch(input_folder: str, output_folder: str, ext: str = "png", 
                 use_general: bool = False, **detector_params) -> None:
    """
    Process batch of images for line detection.
    
    Args:
        input_folder: Input directory path
        output_folder: Output directory path
        ext: Image file extension
        use_general: Whether to use GeneralLineDetector
        **detector_params: Parameters for detector
    """
    os.makedirs(output_folder, exist_ok=True)
    image_paths = glob(os.path.join(input_folder, f"*.{ext}"))
    
    for image_path in image_paths:
        filename = os.path.basename(image_path)
        output_path = os.path.join(output_folder, filename)
        print(f"Processing {filename}")
        process_image(image_path, output_path, use_general=use_general, **detector_params)


# Preset configurations for different line types
THICK_BORDER_CONFIG = {
    'template_length': 100,
    'thickness': 7,
    'border_thickness': 35,
    'threshold': 0.1,
    'angles': [2, -2],
    'use_general': False
}

THIN_BORDER_CONFIG = {
    'template_length': 30,
    'thickness': 7,
    'border_thickness': 20,
    'threshold': 0.1,
    'angles': [2, -2],
    'use_general': False
}

GENERAL_CONFIG = {
    'template_length': 300,
    'thickness': 20,
    'threshold': 0.1,
    'angles': [2, -2],
    'use_general': True  # Use GeneralLineDetector - no border restrictions
}


if __name__ == "__main__":
    # Example usage with general configuration
    process_batch(
        "/Users/irconde/Downloads/V2_170225_exp250225/bin-select",         # input folder
        "/Users/irconde/Downloads/V2_170225_exp250225/border_grid_detection_select",  # output folder
        **THICK_BORDER_CONFIG
    )
