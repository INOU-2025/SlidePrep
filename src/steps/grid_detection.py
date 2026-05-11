from typing import Any

from src.core.step_result import StepResult
from src.config import GridDetectionConfig
from src.core.step import PipelineStep
from src.utils.detection.adaptive_detector import AdaptiveLineDetector


class GridDetectionStep(PipelineStep):
    """Detect grid lines in an image using adaptive template matching."""

    def __init__(self, config: GridDetectionConfig) -> None:
        """Initialize the detection step.

        Args:
            config: Configuration object for the adaptive detector.
        """
        super().__init__(name="grid_detection", config=config)

        try:
            self.detector = AdaptiveLineDetector(config, logger=self.logger)
            self.log(f"Initialized adaptive detector with optimizations: "
                     f"cache={self.detector.enable_template_cache}, "
                     f"early_exit={self.detector.enable_early_exit}")
        except Exception as e:
            self.error(f"Failed to initialize adaptive detector: {e}")
            raise

    def run(self, data: Any) -> StepResult:
        """Run adaptive grid detection on the provided image.

        Args:
            data: Grayscale image array to analyze.

        Returns:
            :class:`~api.schemas.StepResult` containing detection data and metadata.
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

            return StepResult.from_data(results, metadata)

        except Exception as e:
            self.error(f"Adaptive grid detection failed: {e}")
            return StepResult.from_data(None, None)

