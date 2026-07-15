import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.event_bus import EventBus

# Create temporary local event list for test asserts
received_group_a = []
received_group_b = []

async def on_event_group_a(event):
    print(f"[Group A] Received event: {event}")
    received_group_a.append(event)

async def on_event_group_b(event):
    print(f"[Group B] Received event: {event}")
    received_group_b.append(event)

async def main():
    print("Testing Redis Streams consumer group isolation...")
    
    # Initialize separate EventBus to isolate connection pools
    eb = EventBus()
    await eb.connect(settings.REDIS_URL)
    
    if eb._fallback_mode or not eb._redis:
        print("[SKIP] Redis is not running or EventBus fell back to in-memory mode. Skipping group isolation verification.")
        return

    stream_name = "test:group:isolation:v1"
    
    # Clean any old test stream/groups if they exist to start fresh
    try:
        await eb._redis.delete(stream_name)
    except Exception:
        pass

    # Subscribe Group A
    await eb.subscribe(
        stream=stream_name,
        handler=on_event_group_a,
        group_name="test_group_a",
        consumer_name="consumer_a"
    )

    # Subscribe Group B
    await eb.subscribe(
        stream=stream_name,
        handler=on_event_group_b,
        group_name="test_group_b",
        consumer_name="consumer_b"
    )

    # Allow listener task registration loops to start
    await asyncio.sleep(1)

    # Publish test event
    test_event = {"msg": "Hello Group Isolation!"}
    print(f"Publishing event to {stream_name}...")
    await eb.publish(stream_name, test_event)

    # Wait for consumer loops to pull and process
    print("Waiting for consumers to process event...")
    for _ in range(30):
        await asyncio.sleep(0.5)
        if len(received_group_a) >= 1 and len(received_group_b) >= 1:
            break

    # Asserts
    print(f"Group A received counts: {len(received_group_a)}")
    print(f"Group B received counts: {len(received_group_b)}")
    
    assert len(received_group_a) == 1, "Group A failed to receive the event copy!"
    assert len(received_group_b) == 1, "Group B failed to receive the event copy!"
    assert received_group_a[0]["msg"] == "Hello Group Isolation!", "Group A event data is corrupt!"
    assert received_group_b[0]["msg"] == "Hello Group Isolation!", "Group B event data is corrupt!"

    print("[OK] Event successfully processed by both distinct consumer groups independently!")
    
    # Cleanup stream and connection
    await eb._redis.delete(stream_name)
    if eb._redis:
        await eb._redis.aclose()

if __name__ == "__main__":
    asyncio.run(main())
