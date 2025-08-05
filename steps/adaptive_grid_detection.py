"""
Grid detection step using the adaptive line detector.
"""

import cv2
import numpy as np
from typing import Any, Dict
from core.step import PipelineStep
from config.config_schema import GridDetectionConfig
from utils.config_helpers import create_detector_from_grid_config


class AdaptiveGridDetectionStep(PipelineStep):
    """Pipeline step for adaptive grid detection."""
    
    def __init__(self, name: str = "adaptive_grid_detection", config: GridDetectionConfig = None, **kwargs):
        """Initialize adaptive grid detection step."""
        super().__init__(name, config, **kwargs)
        
        if config is None:
            raise ValueError(f"[{name}] GridDetectionConfig is required")
        
        # Create adaptive detector directly from grid config
        try:
            self.detector = create_detector_from_grid_config(config)
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
            
            # Log cache performance
            if 'cache_stats' in results:
                stats = results['cache_stats']
                self.debug(f"Cache performance - Template: {stats['template_hits']}/{stats['template_hits'] + stats['template_misses']}, "
                          f"Preprocessing: {stats['preprocessing_hits']}/{stats['preprocessing_hits'] + stats['preprocessing_misses']}")
            
            # Save debug visualization
            if self.debugger:
                visualization = self.detector.create_visualization(data, results)
                self.debugger.save_debug_image(
                    f"{self.name}_result.png",
                    data,
                    visualization,
                    metadata={
                        'detector': self.detector,
                        'results': results,
                        'horizontal_count': horizontal_count,
                        'vertical_count': vertical_count
                    }
                )
            
            return {
                'horizontal_lines': horizontal_count,
                'vertical_lines': vertical_count,
                'total_lines': horizontal_count + vertical_count,
                'detection_results': results,
                'strategies_used': strategies,
                'cache_stats': results.get('cache_stats', {}),
                'success': True
            }
            
        except Exception as e:
            self.error(f"Adaptive grid detection failed: {e}")
            return {
                'horizontal_lines': 0,
                'vertical_lines': 0,
                'total_lines': 0,
                'detection_results': None,
                'strategies_used': {},
                'cache_stats': {},
                'success': False,
                'error': str(e)
            }