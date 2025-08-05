"""
Grid detection step using the adaptive line detector.
"""

import cv2
import numpy as np
from typing import Any, Dict
from core.step import PipelineStep
from config.config_schema import GridDetectionConfig
from utils.detection.adaptive_detector import AdaptiveLineDetector


class AdaptiveGridDetectionStep(PipelineStep):
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
            
            # Extract detection counts
            detections = results['detections']
            strategies = results['strategies']
            
            horizontal_count = 0
            vertical_count = 0
            
            if 'horizontal' in detections:
                mask, contours = detections['horizontal']
                horizontal_count = len([c for c in contours if cv2.contourArea(c) >= self.detector.min_contour_area])
            
            if 'vertical' in detections:
                mask, contours = detections['vertical']
                vertical_count = len([c for c in contours if cv2.contourArea(c) >= self.detector.min_contour_area])
            
            # Log results
            self.log(f"Detection completed: {horizontal_count} horizontal lines, {vertical_count} vertical lines")
            
            for orientation, strategy in strategies.items():
                if strategy:
                    self.debug(f"  {orientation}: found using {strategy.value}")
                else:
                    self.debug(f"  {orientation}: not found")
            
            # Log cache performance with correct field names
            if 'cache_stats' in results:
                stats = results['cache_stats']
                template_total = stats['template_cache_hits'] + stats['template_cache_misses']
                preprocessing_total = stats['preprocessing_cache_hits'] + stats['preprocessing_cache_misses']
                self.debug(f"Cache performance - Template: {stats['template_cache_hits']}/{template_total}, "
                          f"Preprocessing: {stats['preprocessing_cache_hits']}/{preprocessing_total}")
            
            # Save debug visualization using debugger system instead of detector method
            if self.debugger:
                # Use the debugger's save_debug_image method with drawer integration
                metadata = {
                    'detector': self.detector,
                    'timing': 0,  # Pipeline step doesn't track timing separately
                    'filename': f"{self.name}_result.png",
                    'total_lines_found': horizontal_count + vertical_count,
                    'horizontal_count': horizontal_count,
                    'vertical_count': vertical_count,
                    'strategies_used': strategies
                }
                
                self.debugger.save_debug_image(
                    f"{self.name}_result.png",
                    data,
                    results,
                    metadata
                )
            
            return results['detections']
            
        except Exception as e:
            self.error(f"Adaptive grid detection failed: {e}")
            return None