from typing import Any, Optional

from src.core.step import PipelineStep
from config.config_schema import GridDetectionConfig
from src.utils.detection.adaptive_detector import AdaptiveLineDetector


class GridDetectionStep(PipelineStep):
    """Detect grid lines in an image using adaptive template matching."""

    def __init__(
        self,
        name: str = "grid_detection",
        config: Optional[GridDetectionConfig] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the detection step.

        Args:
            name: Name for logging and debugging purposes.
            config: Configuration object for the adaptive detector.
            **kwargs: Additional parameters forwarded to :class:`PipelineStep`.
        """
        super().__init__(name, config, **kwargs)

        if config is None:
            raise ValueError(f"[{name}] GridDetectionConfig is required")

        try:
            self.detector = AdaptiveLineDetector(config)
            self.log(f"Initialized adaptive detector with optimizations: "
                     f"cache={self.detector.enable_template_cache}, "
                     f"early_exit={self.detector.enable_early_exit}")
        except Exception as e:
            self.error(f"Failed to initialize adaptive detector: {e}")
            raise

    def run(self, data: Any) -> tuple[Any, Optional[dict]]:
        """Run adaptive grid detection on the provided image.

        Args:
            data: Grayscale image array to analyze.

        Returns:
            A tuple with detection results and optional metadata.
        """
        self._validate_image_input(data)

        self.log(
            f"Starting adaptive grid detection on image shape: {data.shape}")

        try:
            # Run adaptive detection
            results = self.detector.detect_lines(data)

            self.log("Detection completed.")

            strategies = results['strategies']
            metadata = self.detector.get_detection_metadata()

            for orientation, strategy in strategies.items():
                orientation_str = orientation.value if hasattr(
                    orientation, 'value') else str(orientation)
                if strategy:
                    self.debug(
                        f"  {orientation_str}: found using {strategy.value}")
                else:
                    self.debug(f"  {orientation_str}: not found")

            # Log cache performance (get from detector)
            cache_stats = self.detector.get_cache_info()
            template_total = (
                cache_stats["template_cache_hits"]
                + cache_stats["template_cache_misses"]
            )
            preprocessing_total = (
                cache_stats["preprocessing_cache_hits"]
                + cache_stats["preprocessing_cache_misses"]
            )
            self.debug(
                "Cache performance - Template: "
                f"{cache_stats['template_cache_hits']}/{template_total}, "
                "Preprocessing: "
                f"{cache_stats['preprocessing_cache_hits']}/{preprocessing_total}"
            )

            return results, metadata

        except Exception as e:
            self.error(f"Adaptive grid detection failed: {e}")
            return None, None
