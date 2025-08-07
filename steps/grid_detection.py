"""
Grid detection step using the adaptive line detector.
"""

import cv2
import numpy as np
from typing import Any, Dict
from core.step import PipelineStep
from config.config_schema import GridDetectionConfig
from utils.detection.adaptive_detector import AdaptiveLineDetector


class GridDetectionStep(PipelineStep):
    """Pipeline step for adaptive grid detection."""
    
    def __init__(self, name: str = "adaptive_grid_detection", config: GridDetectionConfig = None, **kwargs):
        """Initialize adaptive grid detection step."""
        super().__init__(name, config, **kwargs)
        
        if config is None:
            raise ValueError(f"[{name}] GridDetectionConfig is required")
        
        # Create adaptive detector directly from grid config
        try:
            self.detector = AdaptiveLineDetector(config)
            self.log(f"Initialized adaptive detector with optimizations: "
                    f"cache={self.detector.enable_template_cache}, "
                    f"early_exit={self.detector.enable_early_exit}")
        except Exception as e:
            self.error(f"Failed to initialize adaptive detector: {e}")
            raise
    
    def run(self, data: Any) -> Dict[str, Any]:
        """Run adaptive grid detection on input image."""
        self._validate_image_input(data)
        
        self.log(f"Starting adaptive grid detection on image shape: {data.shape}")
        
        try:
            # Run adaptive detection
            results = self.detector.detect_lines(data)

            # TODO. Delete this
            self.detector.analyze_results(results)
            
            # Extract detection counts and strategies
            detections = results['detections']
            strategies = results['strategies']

            metadata = self.detector.get_detection_metadata()
            
            horizontal_count = 0
            vertical_count = 0
            
            if 'horizontal' in detections:
                contours = detections['horizontal']
                horizontal_count = len(contours)  # Contours are pre-filtered by detector
            
            if 'vertical' in detections:
                contours = detections['vertical']
                vertical_count = len(contours)  # Contours are pre-filtered by detector
            
            # Log results
            self.log(f"Detection completed: {horizontal_count} horizontal lines, {vertical_count} vertical lines")
            
            for orientation, strategy in strategies.items():
                if strategy:
                    self.debug(f"  {orientation}: found using {strategy.value}")
                else:
                    self.debug(f"  {orientation}: not found")
            
            # Log cache performance (get from detector)
            cache_stats = self.detector.get_cache_info()
            template_total = cache_stats['template_cache_hits'] + cache_stats['template_cache_misses']
            preprocessing_total = cache_stats['preprocessing_cache_hits'] + cache_stats['preprocessing_cache_misses']
            self.debug(f"Cache performance - Template: {cache_stats['template_cache_hits']}/{template_total}, "
                      f"Preprocessing: {cache_stats['preprocessing_cache_hits']}/{preprocessing_total}")
            
            return results, metadata
            
        except Exception as e:
            self.error(f"Adaptive grid detection failed: {e}")
            return None, None