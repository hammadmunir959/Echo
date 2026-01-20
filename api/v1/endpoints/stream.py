from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as redis
import os
import json
import asyncio

router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

@router.websocket("/meetings/{meeting_id}")
async def websocket_endpoint(websocket: WebSocket, meeting_id: int):
    """
    Real-Time stream of transcript and summary events for a meeting.
    """
    await websocket.accept()
    
    # Create Redis PubSub connection
    r = redis.from_url(REDIS_URL)
    pubsub = r.pubsub()
    channel = f"meeting:{meeting_id}"
    await pubsub.subscribe(channel)
    
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                # Decode and send to WebSocket
                data = message['data'].decode('utf-8')
                await websocket.send_text(data)
            await asyncio.sleep(0.1) # Prevent tight loop burning CPU
    except WebSocketDisconnect:
        # Cleanup
        await pubsub.unsubscribe(channel)
        await r.close()
    except Exception as e:
        print(f"WebSocket Error: {e}")
        await websocket.close()
