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
    """Configurable logging wrapper.

    Provides a unified logging interface that can output to files, console
    or arbitrary file-like streams. This enables deployments in
    environments without filesystem access while maintaining compatibility
    with the standard logging API.
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
        """Configure logging handlers.

        Creates file, console or stream handlers according to ``log_config``.
        Stream handlers allow operation without filesystem access.

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

        if log_config.log_to_file:
            handler: logging.Handler | None = None
            if log_config.stream is not None:
                handler = logging.StreamHandler(log_config.stream)
            elif log_config.log_file_name:
                log_path = log_config.path or "."
                try:
                    os.makedirs(log_path, exist_ok=True)
                    handler = logging.FileHandler(
                        os.path.join(log_path, log_config.log_file_name), mode="w"
                    )
                except OSError:
                    handler = None
            if handler:
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)

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
