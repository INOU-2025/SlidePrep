"""
Dependency Injection Container

Provides a centralized way to manage application services and dependencies.
Supports both singleton and factory patterns.
"""

from typing import Any, Callable, Dict, Optional


class Container:
    """Simple dependency injection container for managing application services."""
    
    _factories: Dict[str, Callable] = {}
    _singletons: Dict[str, Any] = {}

    @classmethod
    def register_factory(cls, name: str, factory: Callable) -> None:
        """
        Register a factory function that creates a new instance each time.
        
        Args:
            name: Service name/key
            factory: Function that returns a new instance when called
        """
        cls._factories[name] = factory

    @classmethod
    def register_singleton(cls, name: str, provider: Any) -> None:
        """
        Register a singleton service that returns the same instance.
        
        Args:
            name: Service name/key  
            provider: Either an instance or a callable that returns an instance
        """
        cls._singletons[name] = provider if not callable(provider) else provider()

    @classmethod
    def resolve(cls, name: str) -> Any:
        """
        Resolve a service by name.
        
        Args:
            name: Service name/key
            
        Returns:
            Service instance (singleton or new factory instance)
            
        Raises:
            KeyError: If service is not registered
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
        Check if a service is registered.
        
        Args:
            name: Service name/key
            
        Returns:
            True if service is registered, False otherwise
        """
        return name in cls._singletons or name in cls._factories

    @classmethod
    def clear(cls) -> None:
        """Clear all registered services. Useful for testing."""
        cls._factories.clear()
        cls._singletons.clear()

    @classmethod
    def list_services(cls) -> Dict[str, str]:
        """
        List all registered services and their types.
        
        Returns:
            Dictionary mapping service names to their types (singleton/factory)
        """
        services = {}
        for name in cls._singletons:
            services[name] = "singleton"
        for name in cls._factories:
            services[name] = "factory"
        return services
