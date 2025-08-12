"""
Application Bootstrap

Sets up the dependency injection container with all required services.
Call bootstrap() once at application startup to initialize services.
"""

from src.core.container import Container
from src.core.logger import Logger
from src.core.debugger import Debugger
from src.core.app_config_manager import AppConfigManager
from src.utils import config_manager
from src.utils.debug.drawer import Drawer
from src.utils.debug.result_writer import ResultWriter
from typing import Optional
from src.core.context import PipelineContext
import os
import cv2
import glob
from src.utils import get_supported_image_patterns


def bootstrap(config_path: str, drawer: Optional[Drawer] = None, writer: Optional[ResultWriter] = None) -> None:
    """
    Initialize the application container with all required services.

    Args:
        config_path: Path to the configuration file
        drawer: Optional drawer to attach to the debugger
        writer: Optional result writer to attach to the debugger
    """
    config_manager = AppConfigManager(config_path)
    Container.register_singleton("config", config_manager)

    logger = Logger(
        config_manager.log_config,
        enabled=config_manager.logger_active
    )
    Container.register_singleton("logger", logger)

    debugger = Debugger(logger, config_manager.debug_config,
                        config_manager.debug_active, drawer=drawer, writer=writer)
    Container.register_singleton("debugger", debugger)

    context = PipelineContext()
    input_path = config_manager.general_config.input_path
    test_cfg = config_manager.test_config
    if test_cfg and test_cfg.input_path and test_cfg.input_type != "data":
        input_path = test_cfg.input_path
    image_shape = None
    if input_path and os.path.isdir(input_path):
        patterns = get_supported_image_patterns()
        for pattern in patterns:
            for fname in glob.glob(os.path.join(input_path, pattern)):
                img = cv2.imread(fname, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    image_shape = (img.shape[0], img.shape[1])
                    break
            if image_shape is not None:
                break
    context.image_shape = image_shape

    Container.register_singleton("pipeline_context", context)


def get_config() -> AppConfigManager:
    """Get the configuration manager from container."""
    return Container.resolve("config")


def get_logger() -> Logger:
    """Get the logger from container."""
    return Container.resolve("logger")


def get_debugger() -> Debugger:
    """Get the debugger from container."""
    return Container.resolve("debugger")


def get_pipeline_context() -> PipelineContext:
    """Get the pipeline context from container."""
    return Container.resolve("pipeline_context")
