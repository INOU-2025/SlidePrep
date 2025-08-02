import cv2
import numpy as np
from typing import Dict, Tuple

from core.step import PipelineStep
from config.config_schema import GridDetectionConfig
from utils.detection import (
    LineTemplateFactory, 
    DetectionStatus, 
    Detection, 
    GridDetectionResult,
    compute_min_required_ratio, 
    border_touch_ratio
)


class GridDetectionStep(PipelineStep):
    """Pipeline step for detecting grid patterns in binarized images."""
    
    def __init__(self, config: GridDetectionConfig, **kwargs):
        """
        Initialize grid detection step.
        
        Args:
            config: Grid detection configuration
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(name="GridDetection", config=config, **kwargs)
        factory = LineTemplateFactory(length=config.line_length, thickness=config.line_thickness, angle_deg=config.angle_deg)
        self.templates = {
            "horizontal": factory.create("horizontal"),
            "vertical": factory.create("vertical")
        }

    def run(self, data: np.ndarray) -> GridDetectionResult:
        """
        Apply grid detection to a binarized image.
        
        Args:
            data: Binarized image as numpy array
            
        Returns:
            GridDetectionResult containing detections and summary statistics
        """
        # Validate input image
        self._validate_image_input(data)

        working_image = data
        self.log(f"Grid detection using binarized image ({working_image.shape[1]}x{working_image.shape[0]})")
        
        detections = []

        # Ensure lines are white for template matching
        mean_val = np.mean(working_image)
        if mean_val < 127:
            inverted = cv2.bitwise_not(working_image)
            self.debug(f"Inverted binary image for template matching (mean={mean_val:.1f})")
        else:
            inverted = working_image
            self.debug(f"Using binary image as-is for template matching (mean={mean_val:.1f})")
        
        thresholds = {
            "horizontal": self.config.horizontal_area_threshold,
            "vertical": self.config.vertical_area_threshold,
            "length": self.config.length_threshold_factor * max(working_image.shape)
        }
        self.debug(f"Length threshold: {thresholds['length']:.1f} (factor: {self.config.length_threshold_factor})")

        stats = {"accept": 0, "reject": 0, "maybe": 0}
        for key, tmpl in self.templates.items():
            t_h, t_w = tmpl.shape
            pad = (t_h // 2, t_w // 2)
            padded = cv2.copyMakeBorder(inverted, *pad, *pad[::-1], cv2.BORDER_CONSTANT, value=0)
            result = cv2.matchTemplate(padded, tmpl, cv2.TM_SQDIFF_NORMED)
            mask = (result < np.percentile(result, self.config.percentile_thresh)).astype(np.uint8) * 255
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                if cv2.contourArea(cnt) >= thresholds[key]:
                    # Correct contour position
                    corrected_contour = cnt + np.array([t_w // 2, t_h // 2]) - [pad[1], pad[0]]
                    
                    # Analyze contour using comprehensive detection logic
                    status, rotated_box = self._analyze_contour(
                        corrected_contour, working_image, key, thresholds
                    )
                    
                    # Create detection object with rotated box
                    detection = Detection(
                        contour=corrected_contour,
                        rotated_box=rotated_box,
                        status=status,
                        orientation=key
                    )
                    detections.append(detection)
                    
                    # Update statistics
                    if status == DetectionStatus.ACCEPT:
                        stats["accept"] += 1
                    elif status == DetectionStatus.REJECT:
                        stats["reject"] += 1
                    elif status == DetectionStatus.MAYBE:
                        stats["maybe"] += 1
            
        self.log(f"Grid detection completed. Accept: {stats['accept']}, Reject: {stats['reject']}, Maybe: {stats['maybe']}")
        
        return GridDetectionResult(detections=detections, summary=stats)

    def _analyze_contour(self, contour: np.ndarray, gray_image: np.ndarray, 
                        line_orientation: str, detection_thresholds: Dict[str, float]) -> Tuple[int, np.ndarray]:
        """
        Analyze a contour using comprehensive detection logic for grid pattern validation.
        
        Args:
            contour: Detected contour (already position-corrected)
            gray_image: Grayscale image
            line_orientation: 'horizontal' or 'vertical'
            detection_thresholds: Dictionary with thresholds
            
        Returns:
            Tuple[int, np.ndarray]: (status, rotated_box)
        """
        area = cv2.contourArea(contour)
        if area == 0:
            return DetectionStatus.REJECT, np.array([])

        # Calculate rotated bounding box
        rotated_rect = cv2.minAreaRect(contour)
        rotated_box = cv2.boxPoints(rotated_rect).astype(np.intp)

        # Calculate dark ratios
        mask = np.zeros_like(gray_image, dtype=np.uint8)
        cv2.fillPoly(mask, [rotated_box], 1)
        dark_ratio = np.count_nonzero((gray_image == 0) & (mask == 1)) / max(np.count_nonzero(mask), 1)

        contour_mask = np.zeros_like(gray_image, dtype=np.uint8)
        cv2.drawContours(contour_mask, [contour], -1, 1, -1)
        contour_dark_ratio = np.count_nonzero((gray_image == 0) & (contour_mask == 1)) / max(np.count_nonzero(contour_mask), 1)

        # Calculate angle and length
        min_ratio = compute_min_required_ratio(area)
        (_, _), (w, h), raw_angle = rotated_rect
        angle = raw_angle + 90 if w < h else raw_angle
        angle = ((angle + 180) % 180) - 90
        length = max(w, h)
        angle_valid = (-4 <= angle <= 4) or (86 <= abs(angle) <= 94)

        # Decision logic
        accepted, maybe, decision = False, False, "REJECT"
        touches, ratio = -1, -1.0

        if dark_ratio >= 0.93:
            accepted, decision = True, "ACCEPT (high confidence)"
        elif dark_ratio < 0.73:
            decision = "REJECT (low confidence)"
        else:
            maybe = True
            decision = "MAYBE (edge case)"
            if length >= detection_thresholds['length']:
                accepted, maybe, decision = True, False, "ACCEPT (length override)"
            elif not angle_valid:
                maybe, decision = False, "REJECT (angle out of bounds)"

        if maybe:
            maybe = False
            touches, ratio = border_touch_ratio(rotated_box, line_orientation, gray_image.shape, self.config.margin)
            if contour_dark_ratio > 0.96 and dark_ratio >= 0.83:
                accepted, decision = True, "ACCEPT (contour ratio override)"
            elif contour_dark_ratio < 0.85 and dark_ratio < 0.80:
                decision = "REJECT (contour ratio override)"
            elif contour_dark_ratio >= 0.80 and dark_ratio >= 0.70 and touches and ratio > 0.9:
                accepted, decision = True, "ACCEPT (relaxed contour-touch override)"
            else:
                accepted, decision = False, "REJECT (not enough evidences)"
            
        # Log analysis details
        self.logger.debug(
            f"grid_detection,{area:.1f},{dark_ratio:.3f},{contour_dark_ratio:.3f},{min_ratio:.3f},"
            f"{length:.1f},{line_orientation},{angle:.2f},{decision},{int(touches)},{ratio:.2f}"
        )

        # Determine final status
        if accepted:
            status = DetectionStatus.ACCEPT
        elif maybe:
            status = DetectionStatus.MAYBE
        else:
            status = DetectionStatus.REJECT

        return status, rotated_box