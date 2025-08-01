from abc import ABC, abstractmethod
from typing import Optional
from core.logger import Logger
from core.debugger import Debugger
from core.context import PipelineContext

class PipelineStep(ABC):
    def __init__(self, name: str, logger: Optional[Logger] = None, debugger: Optional[Debugger] = None):
        self.name = name
        self.logger = logger
        self.debugger = debugger

    @abstractmethod
    def run(self, ctx: PipelineContext) -> None:
        """Perform the operation and update the context."""
        pass

    def log(self, message: str) -> None:
        if self.logger:
            self.logger.info(f"[{self.name}] {message}")

    def debug(self, message: str) -> None:
        if self.logger:
            self.logger.debug(f"[{self.name}] {message}")

    def set_logger(self, logger: Logger) -> None:
        """Set the logger instance."""
        self.logger = logger

    def set_debugger(self, debugger: Debugger) -> None:
        """Set the debugger instance."""
        self.debugger = debugger