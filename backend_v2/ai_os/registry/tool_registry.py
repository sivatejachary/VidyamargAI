import inspect
import logging
from typing import Dict, Any, Callable, List, Type
from pydantic import BaseModel, Field
import threading

logger = logging.getLogger("ai_os.registry.tool_registry")

class ToolMetadata(BaseModel):
    name: str
    description: str
    input_schema: Type[BaseModel]
    permission_required: str
    retry_budget: int = 3
    timeout: float = 30.0

class ToolRegistry:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ToolRegistry, cls).__new__(cls)
                cls._instance._registry = {}
        return cls._instance

    def register(self, name: str, description: str, input_schema: Type[BaseModel], permission: str, retry_budget: int = 3, timeout: float = 30.0) -> Callable:
        """
        Decorator registering an async capability function in the tool register.
        """
        def decorator(func: Callable) -> Callable:
            tool_meta = ToolMetadata(
                name=name,
                description=description,
                input_schema=input_schema,
                permission_required=permission,
                retry_budget=retry_budget,
                timeout=timeout
            )
            # Enforce async signature
            if not inspect.iscoroutinefunction(func):
                raise TypeError(f"Tool registration error: Function '{func.__name__}' for tool '{name}' must be asynchronous.")
            
            self._registry[name] = {"func": func, "meta": tool_meta}
            logger.info(f"Registered tool capability: '{name}' (permission needed: '{permission}')")
            return func
        return decorator

    def get_tool(self, name: str) -> Dict[str, Any]:
        """Returns registered tool executor and metadata."""
        if name not in self._registry:
            raise KeyError(f"Registry capability lookup failed. Tool '{name}' is not registered.")
        return self._registry[name]

    def list_schemas(self) -> List[Dict[str, Any]]:
        """Returns JSON list of registered schemas for model context builders."""
        return [
            {
                "name": v["meta"].name,
                "description": v["meta"].description,
                "input_schema": v["meta"].input_schema.model_json_schema(),
                "permissions": v["meta"].permission_required
            } for k, v in self._registry.items()
        ]

tool_registry = ToolRegistry()
