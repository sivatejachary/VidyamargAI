import asyncio
from typing import Dict, Any, List, Callable, Awaitable

class EventBus:
    """
    Asynchronous event bus for routing notifications, telemetry, and background actions.
    """
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], Awaitable[None]]]] = {}

    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """Register an async handler to listen to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """Unregister an async handler from an event type."""
        if event_type in self._subscribers and handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Publish an event to all registered async handlers concurrently."""
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            return
            
        tasks = []
        for handler in handlers:
            tasks.append(asyncio.create_task(handler(payload)))
            
        # Run all handlers concurrently, catching errors so one handler doesn't block others
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

# Global event bus instance
event_bus = EventBus()
