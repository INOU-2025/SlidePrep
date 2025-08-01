from __future__ import annotations

"""
This class sets up the common components (configuration, logger, debugger)
and offers a run method that executes a given PipelineStep considering a given context. 
After the step runs, the runner can optionally persist the
resulting image through the Debugger's image saving functionality.

This is meant to keep the individual test scripts compact and ensure a consistent
workflow across different steps.
"""

from dataclasses import dataclass
from typing import Iterable, Optional

from core.app_config_manager import AppConfigManager
from core.logger import Logger
from core.debugger import Debugger
from core.context import PipelineContext
from core.step import PipelineStep


@dataclass
class StepTestRunner:

    config_path: str

    def __post_init__(self) -> None:
        # Initialize application configuration
        self.cfg = AppConfigManager.get_instance()
        self.cfg.initialize(self.config_path)

        # Shared logger and debugger instances
        self.logger = Logger.get_instance()
        self.logger.initialize(
            self.cfg.log_config,
            enabled=self.cfg.logger_active,
            output_dir=self.cfg.debug_config.output_dir,
        )

        self.debugger = Debugger.get_instance()
        self.debugger.initialize(self.cfg.debug_config, self.cfg.debug_active)

    def run(
        self,
        step: PipelineStep,
        context: PipelineContext,
        result_attr: Optional[str] = None,
        original_attr: str = "input_image",
    ) -> None:
        """Run ``step`` for each context and optionally save a result image.

        Parameters
        ----------
        step:
            Instantiated pipeline step to execute.
        context:
            :class:`PipelineContext` instance to process.
        result_attr:
            Name of the attribute on ``PipelineContext`` containing the
            result image to persist.  If ``None`` the runner assumes the
            step handles its own debug output.
        original_attr:
            Context attribute containing the original image to compose with
            ``result_attr`` when saving debug imagery.
        """
        
        # Inject logger and debugger into the step
        step.set_logger(self.logger)
        step.set_debugger(self.debugger)
        
        step.run(context)
        if result_attr:
            result_image = getattr(context, result_attr)
            original_image = getattr(context, original_attr, None)
            filename = f"{context.image_name}_{result_attr}.png"
            self.debugger.save_image(filename, result_image, original_image)