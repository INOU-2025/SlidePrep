import argparse
import sys
import cv2
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from steps.grid_detection import GridDetectionStep
from utils.detection import DetectionStatus, GridDetectionResult
from scripts.module_test_runner import StepTestRunner
from core.bootstrap import bootstrap_application


def visualize_grid_detection_results(original_image: np.ndarray, result: GridDetectionResult) -> np.ndarray:
    """
    Create a visualization of grid detection results.
    
    Args:
        original_image: Original grayscale image
        result: Grid detection results
        
    Returns:
        Colored visualization image showing detected grids
    """
    # Convert to color for visualization
    vis_image = cv2.cvtColor(original_image, cv2.COLOR_GRAY2BGR)
    
    # Draw each detection
    for detection in result.detections:
        color = DetectionStatus.get_color(detection.status)
        
        # Draw contour
        cv2.drawContours(vis_image, [detection.contour], -1, color, 2)
        
        # Draw rotated bounding box
        if detection.rotated_box.size > 0:
            cv2.drawContours(vis_image, [detection.rotated_box], -1, color, 2)
            
            # Use the top-left corner of rotated box for text positioning
            text_x, text_y = int(detection.rotated_box[0][0]), int(detection.rotated_box[0][1])
            status_text = DetectionStatus.to_string(detection.status)
            cv2.putText(vis_image, f"{status_text}:{detection.orientation}", 
                       (text_x, text_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    # Add summary statistics
    summary_text = f"Accept: {result.summary['accept']}, Reject: {result.summary['reject']}, Maybe: {result.summary['maybe']}"
    cv2.putText(vis_image, summary_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    return vis_image


def main(config_path: str):
    # Bootstrap the application to get proper logging and configuration
    container = bootstrap_application(config_path)
    logger = container.logger
    
    # Initialize test runner
    runner = StepTestRunner(config_path)
    
    # Create grid detection step with debugger for analysis logging
    step = GridDetectionStep(
        config=runner.cfg.grid_detection_config,
        debugger=container.debugger,
        logger=logger
    )
    
    # Get input directory from config
    input_dir = Path(runner.cfg.test_config.input_dir)
    output_dir = Path(runner.cfg.test_config.output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Processing images from {input_dir}")
    logger.info(f"Output directory: {output_dir}")
    
    # Process each image
    for image_path in input_dir.glob("*.png"):
        logger.info(f"Processing {image_path.name}")
        
        # Load image
        image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            logger.warning(f"Could not load {image_path}")
            continue
            
        # Run grid detection
        result = step.run(image)
        
        # Create visualization
        vis_image = visualize_grid_detection_results(image, result)
        
        # Save visualization
        output_path = output_dir / f"{image_path.stem}_grid_detected.png"
        cv2.imwrite(str(output_path), vis_image)
        
        logger.info(f"Saved visualization: {output_path}")
        logger.info(f"Detection summary: {result.summary}")
        
    logger.info("Grid detection testing completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test grid detection on images")
    parser.add_argument("config", help="Path to test config file")
    args = parser.parse_args()

    main(args.config)