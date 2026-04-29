import asyncio
import structlog
from typing import List

logger = structlog.get_logger("event_bus")

class EventBus:
    def __init__(self):
        self._subscribers: List[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        """Adds a new subscriber queue."""
        q = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers.append(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue):
        """Removes a subscriber queue."""
        async with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    async def publish(self, event: dict):
        """Broadcasts an event to all subscribers."""
        async with self._lock:
            # We iterate over a copy to safely remove failed subscribers if needed
            for q in self._subscribers[:]:
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    # Slow client, drop event for this specific subscriber
                    logger.warning("Event bus queue full, dropping event for subscriber")
                except Exception as e:
                    logger.error("Event bus publish error", error=str(e))

event_bus = EventBus()
