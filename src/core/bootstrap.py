"""
Application Bootstrap

Sets up the dependency injection container with all required services.
Call bootstrap() once at application startup to initialize services.
"""

from src.core.container import Container, build_container
from src.core.logger import Logger
from src.core.debugger import Debugger
from src.core.app_config_manager import AppConfigManager
from src.utils.debug.drawer import Drawer
from src.utils.debug.result_writer import ResultWriter
from typing import Optional
from src.core.context import PipelineContext
import os
import cv2
import glob
from src.utils import get_supported_image_patterns


def bootstrap(
    config_path: str,
    drawer: Optional[Drawer] = None,
    writer: Optional[ResultWriter] = None,
) -> Container:
    """Build and initialize a new :class:`Container` instance."""

    config_manager = AppConfigManager(config_path)

    logger = Logger(config_manager.log_config, enabled=config_manager.logger_active)

    debugger = Debugger(
        logger,
        config_manager.debug_config,
        config_manager.debug_active,
        drawer=drawer,
        writer=writer,
    )

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
    context.image_shape = (image_shape[1], image_shape[0]) if image_shape else None

    container = build_container(logger=logger, debugger=debugger, context=context)
    container.register_singleton("config", config_manager)

    return container
