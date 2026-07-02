"""
Event Bus — decoupled asynchronous communication between agents and services.
"""
import asyncio
import logging
from typing import Callable, Dict, List, Any

logger = logging.getLogger("app.core.events")

# Global subscriber registry
# { event_type: [handler_fn, ...] }
_SUBSCRIBERS: Dict[str, List[Callable]] = {}


def subscribe(event_type: str, handler: Callable):
    """Subscribe a handler function to an event type."""
    if event_type not in _SUBSCRIBERS:
        _SUBSCRIBERS[event_type] = []
    if handler not in _SUBSCRIBERS[event_type]:
        _SUBSCRIBERS[event_type].append(handler)
        logger.info(f"Subscribed handler '{handler.__name__}' to event '{event_type}'")


def unsubscribe(event_type: str, handler: Callable):
    """Unsubscribe a handler function from an event type."""
    if event_type in _SUBSCRIBERS and handler in _SUBSCRIBERS[event_type]:
        _SUBSCRIBERS[event_type].remove(handler)
        logger.info(f"Unsubscribed handler '{handler.__name__}' from event '{event_type}'")


async def publish_event(event_type: str, payload: Any):
    """Publish an event to all registered subscribers concurrently."""
    if event_type not in _SUBSCRIBERS or not _SUBSCRIBERS[event_type]:
        logger.debug(f"No subscribers for event '{event_type}'")
        return

    logger.info(f"Publishing event '{event_type}'")
    handlers = _SUBSCRIBERS[event_type]
    
    tasks = []
    for h in handlers:
        try:
            if asyncio.iscoroutinefunction(h):
                tasks.append(asyncio.create_task(h(payload)))
            else:
                loop = asyncio.get_running_loop()
                tasks.append(asyncio.create_task(loop.run_in_executor(None, h, payload)))
        except Exception as exc:
            logger.error(f"Error preparing handler '{h.__name__}' for event '{event_type}': {exc}")
            
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res, h in zip(results, handlers):
            if isinstance(res, Exception):
                logger.error(f"Handler '{h.__name__}' raised exception for event '{event_type}': {res}")


def publish_event_sync(event_type: str, payload: Any):
    """Publish an event from a synchronous execution context."""
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(publish_event(event_type, payload))
        else:
            asyncio.run(publish_event(event_type, payload))
    except RuntimeError:
        # No running event loop in thread, run standalone
        asyncio.run(publish_event(event_type, payload))
