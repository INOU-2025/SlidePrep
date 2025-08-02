"""
Application Bootstrap

Sets up the dependency injection container with all required services.
Call bootstrap() once at application startup to initialize services.
"""

from core.container import Container
from core.logger import Logger
from core.debugger import Debugger
from core.app_config_manager import AppConfigManager
from utils.debug.base_drawer import BaseDrawer
from typing import Optional


def bootstrap(config_path: str, drawer: Optional[BaseDrawer] = None) -> None:
    """
    Initialize the application container with all required services.

    Args:
        config_path: Path to the configuration file
        drawer: Optional drawer to attach to the debugger
    """
    config_manager = AppConfigManager(config_path)
    Container.register_singleton("config", config_manager)

    logger = Logger(
        config_manager.log_config,
        enabled=config_manager.logger_active
    )
    Container.register_singleton("logger", logger)

    debugger = Debugger(config_manager.debug_config,
                        config_manager.debug_active, drawer=drawer)
    Container.register_singleton("debugger", debugger)


def get_config() -> AppConfigManager:
    """Get the configuration manager from container."""
    return Container.resolve("config")


def get_logger() -> Logger:
    """Get the logger from container."""
    return Container.resolve("logger")


def get_debugger() -> Debugger:
    """Get the debugger from container."""
    return Container.resolve("debugger")
