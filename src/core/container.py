"""
Dependency Injection Container

Provides a centralized way to manage application services and dependencies.
Supports both singleton and factory patterns for flexible service lifecycle
management. Services can be registered as singletons (shared instances) or
factories (new instance per request).
"""

from typing import Any, Callable, Dict, Optional, Union


class Container:
    """
    Simple dependency injection container for managing application services.
    
    This container provides a centralized registry for application services
    with support for both singleton and factory patterns. It enables loose
    coupling between components by allowing services to be resolved by name
    rather than direct instantiation.
    
    The container supports:
    - Singleton services: Single shared instance across the application
    - Factory services: New instance created on each resolution
    - Service existence checking and listing capabilities
    - Complete service registry clearing for testing scenarios
    """

    _factories: Dict[str, Callable[[], Any]] = {}
    _singletons: Dict[str, Any] = {}

    @classmethod
    def register_factory(cls, name: str, factory: Callable[[], Any]) -> None:
        """
        Register a factory function that creates a new instance each time.

        Factory services are useful for stateful objects that should not
        be shared or when different configurations are needed per request.

        Args:
            name: Unique service identifier for resolution
            factory: Zero-argument callable that returns a new service instance
        """
        cls._factories[name] = factory

    @classmethod
    def register_singleton(cls, name: str, provider: Union[Any, Callable[[], Any]]) -> None:
        """
        Register a singleton service that returns the same instance.

        Singleton services are ideal for stateless services, configuration
        objects, or expensive-to-create instances that should be shared.

        Args:
            name: Unique service identifier for resolution
            provider: Either a service instance or a zero-argument callable
                     that returns the instance to be cached
        """
        cls._singletons[name] = provider if not callable(
            provider) else provider()

    @classmethod
    def resolve(cls, name: str) -> Any:
        """
        Resolve a service by name with precedence for singletons.

        Checks singleton registry first, then factory registry. This ensures
        that explicitly registered singleton instances take precedence over
        factory functions with the same name.

        Args:
            name: Service identifier used during registration

        Returns:
            Service instance - either the cached singleton or a new instance
            from the factory function

        Raises:
            KeyError: If no service is registered with the given name
        """
        if name in cls._singletons:
            return cls._singletons[name]
        elif name in cls._factories:
            return cls._factories[name]()
        else:
            raise KeyError(f"Service '{name}' not registered in container")

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        Check if a service is registered in either registry.

        Useful for conditional service resolution or validation before
        attempting to resolve a service that might not exist.

        Args:
            name: Service identifier to check for registration

        Returns:
            True if service exists in either singleton or factory registry,
            False otherwise
        """
        return name in cls._singletons or name in cls._factories

    @classmethod
    def clear(cls) -> None:
        """
        Clear all registered services from both registries.
        
        This method is primarily intended for testing scenarios where
        a clean container state is needed between test cases. In production
        code, services should generally persist for the application lifetime.
        """
        cls._factories.clear()
        cls._singletons.clear()

    @classmethod
    def list_services(cls) -> Dict[str, str]:
        """
        List all registered services and their registration types.

        Provides introspection capabilities for debugging and service
        discovery. Useful for understanding the current container state
        and verifying service registrations.

        Returns:
            Dictionary mapping service names to their registration type
            ('singleton' or 'factory'). If a service is registered in both
            registries, 'singleton' takes precedence in the listing.
        """
        services = {}
        for name in cls._singletons:
            services[name] = "singleton"
        for name in cls._factories:
            services[name] = "factory"
        return services
