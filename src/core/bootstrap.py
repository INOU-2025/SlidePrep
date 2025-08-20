"""
Application Bootstrap

Sets up the dependency injection container with all required services.
Call bootstrap() once at application startup to initialize services.
"""

from typing import Optional, TYPE_CHECKING

from src.core.container import Container, build_container
from src.core.logger import Logger
from src.core.debugger import Debugger
from src.core.app_config_manager import AppConfigManager
from src.utils.debug.drawer import Drawer
from src.utils.debug.result_writer import ResultWriter
from src.core.context import PipelineContext

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from api import AppConfig


def bootstrap(
    config_path: str | None = None,
    drawer: Optional[Drawer] = None,
    writer: Optional[ResultWriter] = None,
    *,
    config: AppConfigManager | "AppConfig" | None = None,
    image_shape: tuple[int, int] | None = None,
) -> Container:
    """Build and initialize a new :class:`Container` instance."""

    if config is not None:
        config_manager = (
            config
            if isinstance(config, AppConfigManager)
            else AppConfigManager.from_app_config(config)
        )
    else:
        if config_path is None:
            raise ValueError("Either config_path or config must be provided")
        config_manager = AppConfigManager(config_path)

    logger = Logger(config_manager.log_config, enabled=config_manager.logger_active)

    debugger = Debugger(
        logger,
        config_manager.debug_config,
        config_manager.debug_active,
        drawer=drawer,
        writer=writer,
    )

    context = PipelineContext(image_shape=image_shape)

    container = build_container(logger=logger, debugger=debugger, context=context)
    container.register_singleton("config", config_manager)

    return container
