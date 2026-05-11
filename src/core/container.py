"""Dependency injection container with context-local storage."""

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Union

from src.config import DebugConfig, LogConfig
from src.core.context import PipelineContext
from src.core.debugger import Debugger
from src.core.logger import Logger


# Context variable holding the container for the current execution context
_current_container: ContextVar["Container | None"] = ContextVar(
    "current_container", default=None
)


@dataclass
class Container:
    """Per-request dependency injection container."""

    _factories: Dict[str, Callable[[], Any]] = field(default_factory=dict)
    _singletons: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Registration and resolution
    # ------------------------------------------------------------------
    def register_factory(self, name: str, factory: Callable[[], Any]) -> None:
        """Register a factory that creates a new instance each time."""

        self._factories[name] = factory

    def register_singleton(self, name: str, provider: Union[Any, Callable[[], Any]]) -> None:
        """Register a singleton service or provider."""

        self._singletons[name] = provider if not callable(provider) else provider()

    def resolve(self, name: str) -> Any:
        """Resolve a service by name with precedence for singletons."""

        if name in self._singletons:
            return self._singletons[name]
        if name in self._factories:
            return self._factories[name]()
        raise KeyError(f"Service '{name}' not registered in container")

    def is_registered(self, name: str) -> bool:
        """Return ``True`` if a service is registered."""

        return name in self._singletons or name in self._factories

    def clear(self) -> None:
        """Remove all registered services."""

        self._factories.clear()
        self._singletons.clear()

    def list_services(self) -> Dict[str, str]:
        """List all registered services with their registration type."""

        services: Dict[str, str] = {}
        for name in self._singletons:
            services[name] = "singleton"
        for name in self._factories:
            services[name] = "factory"
        return services

    # ------------------------------------------------------------------
    # Context management
    # ------------------------------------------------------------------
    @classmethod
    def set_current(cls, container: "Container") -> None:
        """Bind ``container`` to the current execution context."""

        _current_container.set(container)

    @classmethod
    def current(cls) -> "Container":
        """Get the container bound to the current context."""

        container = _current_container.get()
        if container is None:
            raise RuntimeError("No container set for current context")
        return container


def build_container(
    *,
    logger: Logger | None = None,
    debugger: Debugger | None = None,
    context: PipelineContext | None = None,
) -> Container:
    """Create and bind a fresh container for the current context.

    The container is pre-populated with ``logger``, ``debugger`` and a
    ``PipelineContext``. If any of these are not provided, default instances
    are created.
    """

    container = Container()

    if logger is None:
        logger = Logger(LogConfig())
    if debugger is None:
        debugger = Debugger(logger, DebugConfig(), True)
    if context is None:
        context = PipelineContext()

    container.register_singleton("logger", logger)
    container.register_singleton("debugger", debugger)
    container.register_singleton("pipeline_context", context)

    Container.set_current(container)
    return container
