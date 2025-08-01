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
    _instance = None

    def __new__(cls, *args, **kwargs):
        raise RuntimeError("Use 'Logger.get_instance()' to access the Logger instance.")

    @classmethod
    def get_instance(cls) -> "Logger":
        if not cls._instance:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialized = False
            cls._instance._enabled = False
            cls._instance.logger = NoOpLogger()  # Default to NoOp until initialized
        return cls._instance

    @property
    def enabled(self) -> bool:
        """
        Property to check if logging is enabled.
        """
        return self._enabled

    def initialize(self, log_config: LogConfig, enabled: bool = True) -> None:
        """
        Initialize the Logger instance with the given configuration.
        """
        if self._initialized:
            return
        self._enabled = enabled
        if not self._enabled:
            self.logger = NoOpLogger()
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(getattr(logging, log_config.log_level.upper(), logging.INFO))
            self._setup_handlers(log_config)
        self._initialized = True

    def _setup_handlers(self, log_config: LogConfig) -> None:
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        log_format = "%(asctime)s %(levelname)s %(message)s"
        formatter = logging.Formatter(log_format)

        if log_config.log_to_file and log_config.log_file_name:
            os.makedirs(log_config.output_dir, exist_ok=True)
            file_handler = logging.FileHandler(os.path.join(log_config.output_dir, log_config.log_file_name), mode='w')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        if log_config.log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def info(self, *args, **kwargs) -> None:
        if not self._initialized:
            self._auto_initialize()
        self.logger.info(*args, **kwargs)

    def error(self, *args, **kwargs) -> None:
        if not self._initialized:
            self._auto_initialize()
        self.logger.error(*args, **kwargs)

    def exception(self, *args, **kwargs) -> None:
        if not self._initialized:
            self._auto_initialize()
        self.logger.exception(*args, **kwargs)

    def debug(self, *args, **kwargs) -> None:
        if not self._initialized:
            self._auto_initialize()
        self.logger.debug(*args, **kwargs)
    
    def warning(self, *args, **kwargs) -> None:
        if not self._initialized:
            self._auto_initialize()
        self.logger.warning(*args, **kwargs)
    
    def _auto_initialize(self) -> None:
        """Auto-initialize with basic console logging if not manually initialized."""
        if not self._initialized:
            basic_config = LogConfig(
                log_to_console=True,
                log_to_file=False,
                log_level="INFO"
            )
            self.initialize(basic_config, enabled=True)