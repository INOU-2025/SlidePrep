import logging
import os
from typing import Any, Union
from config.config_schema import LogConfig


class NoOpLogger:
    """
    No-operation logger for disabled logging scenarios.
    
    Provides a null object pattern implementation that accepts all logging
    calls but performs no actual logging operations. This allows the same
    logging interface to be used throughout the application regardless of
    whether logging is enabled, avoiding conditional checks at call sites.
    """

    def info(self, *args: Any, **kwargs: Any) -> None:
        """No-op info logging method."""
        pass
    
    def error(self, *args: Any, **kwargs: Any) -> None:
        """No-op error logging method."""
        pass
    
    def exception(self, *args: Any, **kwargs: Any) -> None:
        """No-op exception logging method."""
        pass
    
    def debug(self, *args: Any, **kwargs: Any) -> None:
        """No-op debug logging method."""
        pass
    
    def warning(self, *args: Any, **kwargs: Any) -> None:
        """No-op warning logging method."""
        pass

    def critical(self, *args: Any, **kwargs: Any) -> None:
        """No-op critical logging method."""
        pass


class Logger:
    """
    Logger wrapper with configurable handlers and output destinations.
    
    Provides a unified logging interface that can output to both file and
    console based on configuration. Supports dynamic handler setup and
    graceful degradation to no-op logging when disabled.
    
    The logger automatically creates output directories and configures
    appropriate formatters for different output destinations. It maintains
    compatibility with the standard logging interface while providing
    additional configuration flexibility.
    """

    def __init__(self, log_config: LogConfig, enabled: bool = True) -> None:
        """
        Initialize the Logger instance with the given configuration.

        Sets up the logging infrastructure based on the provided configuration,
        including file and console handlers as specified. When disabled,
        uses a no-op logger to maintain interface compatibility.

        Args:
            log_config: Logging configuration specifying level, destinations,
                       file names, and output directories
            enabled: Whether logging operations should be performed or no-op
        """
        self._enabled = enabled
        if not self._enabled:
            self.logger: Union[logging.Logger, NoOpLogger] = NoOpLogger()
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(
                getattr(logging, log_config.log_level.upper(), logging.INFO))
            self._setup_handlers(log_config)

    @property
    def enabled(self) -> bool:
        """
        Check if logging is enabled.
        
        Returns:
            True if logging operations are active, False if using no-op logger
        """
        return self._enabled

    def _setup_handlers(self, log_config: LogConfig) -> None:
        """
        Set up file and console handlers based on configuration.
        
        Configures the underlying logging infrastructure with appropriate
        handlers for file and console output. Creates necessary directories
        and applies consistent formatting across all handlers.
        
        Args:
            log_config: Configuration specifying output destinations and formats
        """
        # Only proceed if we have a real logger (not NoOpLogger)
        if not isinstance(self.logger, logging.Logger):
            return
            
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        log_format = "%(asctime)s %(levelname)s %(message)s"
        formatter = logging.Formatter(log_format)

        if log_config.log_to_file and log_config.log_file_name:
            log_path = log_config.path or "."
            os.makedirs(log_path, exist_ok=True)
            file_handler = logging.FileHandler(os.path.join(
                log_path, log_config.log_file_name), mode='w')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        if log_config.log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def info(self, *args: Any, **kwargs: Any) -> None:
        """Log an informational message."""
        self.logger.info(*args, **kwargs)

    def error(self, *args: Any, **kwargs: Any) -> None:
        """Log an error message."""
        self.logger.error(*args, **kwargs)

    def exception(self, *args: Any, **kwargs: Any) -> None:
        """Log an exception with full traceback information."""
        self.logger.exception(*args, **kwargs)

    def debug(self, *args: Any, **kwargs: Any) -> None:
        """Log a debug message for development and troubleshooting."""
        self.logger.debug(*args, **kwargs)

    def warning(self, *args: Any, **kwargs: Any) -> None:
        """Log a warning message for potentially problematic situations."""
        self.logger.warning(*args, **kwargs)

    def critical(self, *args: Any, **kwargs: Any) -> None:
        """Log a critical message for fatal errors that prevent operation."""
        self.logger.critical(*args, **kwargs)
