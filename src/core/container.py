"""
Dependency Injection Container

Provides a centralized way to manage application services and dependencies.
Supports both singleton and factory patterns for flexible service lifecycle
management. Services can be registered as singletons (shared instances) or
factories (new instance per request).
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Union


@dataclass
class Container:
    """Per-request dependency injection container."""

    _factories: Dict[str, Callable[[], Any]] = field(default_factory=dict)
    _singletons: Dict[str, Any] = field(default_factory=dict)

    def register_factory(self, name: str, factory: Callable[[], Any]) -> None:
        """Register a factory function that creates a new instance each time."""

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
        """Return True if a service is registered."""

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
