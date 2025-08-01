import cv2
import numpy as np
import os
from typing import Dict, Tuple

from core.step import PipelineStep
from config.config_schema import GridDetectionConfig
from utils.detection.line_template_factory import LineTemplateFactory
from utils.debug.grid_detection_drawer import GridDetectionDrawer
from utils.detection.analysis import draw_and_analyze_contour


class GridDetectionStep(PipelineStep):
    def __init__(self, config: GridDetectionConfig, **kwargs):
        super().__init__(name="GridDetection", **kwargs)
        self.config = config
        factory = LineTemplateFactory(length=config.line_length, thickness=config.line_thickness, angle_deg=config.angle_deg)
        self.templates = {
            "horizontal": factory.create("horizontal"),
            "vertical": factory.create("vertical")
        }

    def run(self, data: np.ndarray) -> Tuple[np.ndarray, Dict[str, int]]:
        """
        Apply grid detection to a binarized image.
        
        Args:
            data: Binarized image as numpy array
            
        Returns:
            Tuple of (processed_image, statistics_dict)
        """
        if data is None:
            raise ValueError("Binarized image is required for grid detection")

        working_image = data
        self.log(f"Grid detection using binarized image ({working_image.shape[1]}x{working_image.shape[0]})")
        
        # Create output image for visualization (copy of input)
        output_image = working_image.copy()
        
        # Create drawer for debug visualization if enabled
        drawer = None
        if self.debugger and self.debugger.is_enabled():
            # Convert to BGR for visualization
            visualization_base = cv2.cvtColor(working_image, cv2.COLOR_GRAY2BGR)
            drawer = self.debugger.create_drawer("grid_detection", visualization_base)

        # Ensure lines are white for template matching
        mean_val = np.mean(working_image)
        if mean_val < 127:  # Most pixels are dark, likely lines are black
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
                    a, r, m = draw_and_analyze_contour(
                        cnt, working_image, key, np.array([t_w // 2, t_h // 2]) - [pad[1], pad[0]],
                        thresholds, drawer, "grid_detection", self.config.margin, self.logger
                    )
                    stats["accept"] += a
                    stats["reject"] += r
                    stats["maybe"] += m

        if drawer:
            drawer.save("grid_detection")
            
        self.log(f"Grid detection completed. Accept: {stats['accept']}, Reject: {stats['reject']}, Maybe: {stats['maybe']}")
        
        return output_image, stats