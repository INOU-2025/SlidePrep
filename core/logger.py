import logging
import os
from config.config_schema import LogConfig

class NoOpLogger:
    def info(self, *args, **kwargs) -> None: pass
    def error(self, *args, **kwargs) -> None: pass
    def exception(self, *args, **kwargs) -> None: pass
    def debug(self, *args, **kwargs) -> None: pass
    def warning(self, *args, **kwargs) -> None: pass

class Logger:
    def __init__(self, log_config: LogConfig, enabled: bool = True):
        """
        Initialize the Logger instance with the given configuration.
        
        Args:
            log_config: Logging configuration
            enabled: Whether logging is enabled
        """
        self._enabled = enabled
        if not self._enabled:
            self.logger = NoOpLogger()
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(getattr(logging, log_config.log_level.upper(), logging.INFO))
            self._setup_handlers(log_config)

    @property
    def enabled(self) -> bool:
        """
        Property to check if logging is enabled.
        """
        return self._enabled

    def _setup_handlers(self, log_config: LogConfig) -> None:
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        log_format = "%(asctime)s %(levelname)s %(message)s"
        formatter = logging.Formatter(log_format)

        if log_config.log_to_file and log_config.log_file_name:
            output_dir = log_config.output_dir or "."
            os.makedirs(output_dir, exist_ok=True)
            file_handler = logging.FileHandler(os.path.join(output_dir, log_config.log_file_name), mode='w')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        if log_config.log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def info(self, *args, **kwargs) -> None:
        self.logger.info(*args, **kwargs)

    def error(self, *args, **kwargs) -> None:
        self.logger.error(*args, **kwargs)

    def exception(self, *args, **kwargs) -> None:
        self.logger.exception(*args, **kwargs)

    def debug(self, *args, **kwargs) -> None:
        self.logger.debug(*args, **kwargs)
    
    def warning(self, *args, **kwargs) -> None:
        self.logger.warning(*args, **kwargs)