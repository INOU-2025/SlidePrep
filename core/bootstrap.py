"""
Application Bootstrap

Sets up the dependency injection container with all required services.
Call bootstrap() once at application startup to initialize services.
"""

from core.container import Container
from core.logger import Logger
from core.debugger import Debugger
from core.app_config_manager import AppConfigManager


def bootstrap(config_path: str) -> None:
    """Initialize the application container with all required services.
    
    Args:
        config_path: Path to the configuration file
    """
    # Initialize configuration first (singleton)
    config_manager = AppConfigManager(config_path)
    Container.register_singleton("config", config_manager)
    
    # Initialize logger (singleton - shared across the app)
    logger = Logger(
        config_manager.log_config, 
        enabled=config_manager.logger_active
    )
    Container.register_singleton("logger", logger)
    
    # Initialize debugger (singleton - shared across the app)
    debugger = Debugger(config_manager.debug_config, config_manager.debug_active)
    Container.register_singleton("debugger", debugger)


def get_config() -> AppConfigManager:
    """Convenience function to get the configuration manager."""
    return Container.resolve("config")


def get_logger() -> Logger:
    """Convenience function to get the logger."""
    return Container.resolve("logger")


def get_debugger() -> Debugger:
    """Convenience function to get the debugger."""
    return Container.resolve("debugger")
