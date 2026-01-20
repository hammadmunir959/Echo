import logging
from core.celery_app import app
from core.transcriber import transcriber
from core.summarizer import summarizer
from database.db_manager import db_manager
# from core.memory import memory_manager
import json

logger = logging.getLogger("EchoDistributedTasks")

@app.task(name='echo.tasks.transcribe', bind=True, max_retries=3)
def task_transcribe(self, audio_path, meeting_id):
    """
    Asynchronous task to transcribe an audio chunk.
    On success, it enqueues the 'summarize' task.
    """
    logger.info(f"Starting transcription for {audio_path} (Meeting: {meeting_id})")
    try:
        raw_text, segments = transcriber.transcribe(audio_path)
        
        if not raw_text.strip():
            logger.warning(f"No speech detected in {audio_path}. Skipping summary.")
            return {"status": "skipped", "reason": "no_speech"}

        # Save transcript to DB and Get ID
        with db_manager.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO transcripts (meeting_id, raw_text, segments_json) VALUES (?, ?, ?)",
                (meeting_id, raw_text, json.dumps(segments))
            )
            transcript_id = cursor.lastrowid
        
        # Dispatch Summary Task with Traceability ID
        task_summarize.delay(raw_text, meeting_id, transcript_id)
        
        # Real-Time: Publish to Redis Channel
        # Note: app.conf.broker_url usually points to Redis. 
        # We can create a direct redis client or use Celery's connection.
        # For simplicity and robustness, we use a fresh Redis client.
        import redis
        import os
        r_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            r = redis.from_url(r_url)
            event = {
                "type": "transcript",
                "meeting_id": meeting_id,
                "text": raw_text,
                "segments": segments
            }
            r.publish(f"meeting:{meeting_id}", json.dumps(event))
        except Exception as e:
            logger.warning(f"Failed to publish Redis event: {e}")

        return {"status": "success", "text_length": len(raw_text)}
        
    except Exception as exc:
        logger.error(f"Transcription failed: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

@app.task(name='echo.tasks.summarize', bind=True, max_retries=3)
def task_summarize(self, transcript_text, meeting_id, source_transcript_id=None):
    """
    Asynchronous task to extract action items from a transcript.
    Now supports Context Aggregation (TODO: buffering) and Traceability.
    """
    logger.info(f"Starting summarization for Meeting: {meeting_id} (Source: {source_transcript_id})")
    try:
        # 1. Extract Action Items
        action_items = summarizer.extract_action_items(transcript_text)
        
        # 2. Save to DB with Lineage
        with db_manager.get_connection() as conn:
            for item in action_items:
                conn.execute(
                    "INSERT INTO action_items (meeting_id, description, owner, status, source_transcript_id) VALUES (?, ?, ?, ?, ?)",
                    (meeting_id, item['description'], item.get('owner', 'TBD'), 'open', source_transcript_id)
                )

        # 3. RAG: Index Action Items (DISABLED - FUTURE API ADDITION)
        # for item in action_items:
        #     pass

        return {"status": "success", "items_found": len(action_items)}
        
    except Exception as exc:
        logger.error(f"Summarization failed: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
