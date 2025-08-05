"""
Configuration helper utilities for adaptive detection.
"""

from config.config_schema import GridDetectionConfig
from utils.detection.adaptive_detector import AdaptiveLineDetector
from utils.detection.models import DetectionStrategy


def create_detector_from_grid_config(grid_config: GridDetectionConfig) -> AdaptiveLineDetector:
    """
    Create adaptive detector directly from grid detection configuration.
    
    Args:
        grid_config: GridDetectionConfig instance
        
    Returns:
        Configured AdaptiveLineDetector instance
    """
    # Create detector with all optimization settings from config
    detector = AdaptiveLineDetector(
        min_contour_area=grid_config.min_contour_area,
        threshold=grid_config.threshold,
        angles=grid_config.angles,
        enable_early_exit=grid_config.enable_early_exit,
        enable_template_cache=grid_config.enable_template_cache,
        enable_preprocessing_cache=grid_config.enable_preprocessing_cache,
        cache_max_size=grid_config.cache_max_size
    )
    
    # Override strategy configurations with config values
    detector.configs = {
        DetectionStrategy.GENERAL: grid_config.general.copy(),
        DetectionStrategy.THICK_BORDER: grid_config.thick_border.copy(),
        DetectionStrategy.THIN_BORDER: grid_config.thin_border.copy()
    }
    
    return detector