import logging
import os
from typing import Optional

class NoOpLogger:
    def info(self, *args, **kwargs) -> None: pass
    def error(self, *args, **kwargs) -> None: pass
    def exception(self, *args, **kwargs) -> None: pass
    def debug(self, *args, **kwargs) -> None: pass

class Logger:
    _instance = None

    def __new__(cls, *args, **kwargs):
        raise RuntimeError("Use 'Logger.get_instance()' to access the Logger instance.")

    @classmethod
    def get_instance(
        cls, 
        log_to_file: bool = False, 
        log_to_console: bool = True, 
        log_file_name: Optional[str] = None, 
        log_level: str = "INFO", 
        output_dir: str = "logs", 
        disable_logging: bool = False
    ) -> "Logger":
        if not cls._instance:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialized = False
            cls._instance._initialize(log_to_file, log_to_console, log_file_name, log_level, output_dir, disable_logging)
        return cls._instance

    def _initialize(
        self, 
        log_to_file: bool, 
        log_to_console: bool, 
        log_file_name: Optional[str], 
        log_level: str, 
        output_dir: str, 
        disable_logging: bool
    ) -> None:
        if self._initialized:
            return
        if disable_logging:
            self.logger = NoOpLogger()
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
            self._setup_handlers(log_to_file, log_to_console, log_file_name, output_dir)
        self._initialized = True

    def _setup_handlers(
        self, 
        log_to_file: bool, 
        log_to_console: bool, 
        log_file_name: Optional[str], 
        output_dir: str
    ) -> None:
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        log_format = "%(asctime)s %(levelname)s %(message)s"
        formatter = logging.Formatter(log_format)

        if log_to_file and log_file_name:
            os.makedirs(output_dir, exist_ok=True)
            file_handler = logging.FileHandler(os.path.join(output_dir, log_file_name), mode='w')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        if log_to_console:
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