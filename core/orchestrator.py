import time
import json
import logging
from threading import Thread
from database.db_manager import db_manager
from core.task_queue import task_queue
from core.transcriber import transcriber
from core.summarizer import summarizer

logger = logging.getLogger("EchoOrchestrator")

class Orchestrator:
    def __init__(self):
        self.is_running = False
        self.worker_thread = None

    def start_worker(self):
        """Starts the background worker thread."""
        if self.is_running:
            return
        
        self.is_running = True
        self.worker_thread = Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        # Recovery: Reset potential zombie tasks from previous crashes
        task_queue.recover_stalled_tasks()
        
        logger.info("Orchestrator worker started.")

    def stop_worker(self):
        """Stops the worker gracefully."""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join()
        logger.info("Orchestrator worker stopped.")

    def _worker_loop(self):
        """Main loop fetching and executing tasks."""
        while self.is_running:
            try:
                task = task_queue.fetch_next_task()
                if task:
                    self._process_task(task)
                else:
                    time.sleep(1) # Idle poll
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                time.sleep(2)

    def _process_task(self, task):
        """Dispatches task to appropriate handler."""
        task_id = task['id']
        task_type = task['task_type']
        
        # Parse payload safely
        try:
            payload = json.loads(task['payload'])
        except:
            payload = task['payload'] # Fallback if already dict (should be str from DB)

        logger.info(f"Processing task {task_id}: {task_type}")

        try:
            if task_type == 'transcribe':
                self._handle_transcription(task_id, payload)
            elif task_type == 'summarize':
                self._handle_summarization(task_id, payload)
            else:
                logger.warning(f"Unknown task type: {task_type}")
                task_queue.mark_failed(task_id, "Unknown task type")

        except Exception as e:
            logger.error(f"Task processing failed: {e}")
            task_queue.mark_failed(task_id, str(e))

    def _handle_transcription(self, task_id, payload):
        """
        Runs Whisper -> Saves Transcript -> Enqueues Summary Task.
        Payload: { "audio_path": str, "meeting_id": int }
        """
        audio_path = payload.get('audio_path')
        meeting_id = payload.get('meeting_id')
        
        if not audio_path or not meeting_id:
            raise ValueError("Missing audio_path or meeting_id")

        # 1. Transcribe
        text, segments = transcriber.transcribe(audio_path)
        
        if not text:
            logger.info("Empty transcription (silence?), skipping summary.")
            task_queue.mark_completed(task_id)
            return

        # 2. Save to DB
        with db_manager.get_connection() as conn:
            conn.execute(
                "INSERT INTO transcripts (meeting_id, raw_text, segments_json) VALUES (?, ?, ?)",
                (meeting_id, text, json.dumps(segments))
            )

        # 3. Enqueue Summary Task
        summary_payload = {
            "text": text,
            "meeting_id": meeting_id
        }
        task_queue.enqueue_task('summarize', summary_payload)
        
        # 4. Mark Completed
        task_queue.mark_completed(task_id)

    def _handle_summarization(self, task_id, payload):
        """
        Runs Qwen (Rolling context) -> Updates Action Items.
        Payload: { "text": str, "meeting_id": int }
        """
        new_text = payload.get('text')
        meeting_id = payload.get('meeting_id')
        
        # 1. Fetch Previous Summary (Context)
        # Note: In a real rolling summary, we'd store the 'current summary' state. 
        # For this MVP, we will try to fetch the last action item description as context 
        # or just rely on the model to extract new items from new chunks independently.
        # IMPROVEMENT: Add 'summary_state' table or memory.
        # HACK for MVP: Just pass "Previous segments processed." as context or fetch last action items.
        
        previous_summary = "Processed previous meeting segments." # Placeholder for MVP
        
        # 2. Summarize & Extract
        result = summarizer.summarize(new_text, existing_summary=previous_summary)
        
        # Result Schema: { "summary": ..., "action_items": [ ... ] }
        
        # 3. Save Action Items
        action_items = result.get('action_items', [])
        with db_manager.get_connection() as conn:
            for item in action_items:
                conn.execute(
                    "INSERT INTO action_items (meeting_id, description, owner) VALUES (?, ?, ?)",
                    (meeting_id, item.get('task'), item.get('owner'))
                )
        
        logger.info(f"Extracted {len(action_items)} action items.")
        
        # 4. Mark Completed
        task_queue.mark_completed(task_id)

orchestrator = Orchestrator()
