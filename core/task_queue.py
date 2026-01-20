import json
import logging
from database.db_manager import db_manager
from core.config import Config

logger = logging.getLogger("EchoTaskQueue")

class TaskQueue:
    @staticmethod
    def enqueue_task(task_type, payload):
        """Adds a new task to the queue."""
        logger.info(f"Enqueuing task: {task_type}")
        payload_str = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload)
        
        with db_manager.get_connection() as conn:
            conn.execute(
                "INSERT INTO task_queue (task_type, payload) VALUES (?, ?)",
                (task_type, payload_str)
            )

    @staticmethod
    def fetch_next_task():
        """Retrieves the oldest pending task and marks it as processing."""
        with db_manager.get_connection() as conn:
            # We use a transaction to ensure atomic 'fetch and mark'
            row = conn.execute(
                "SELECT * FROM task_queue WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1"
            ).fetchone()
            
            if row:
                conn.execute(
                    "UPDATE task_queue SET status = 'processing' WHERE id = ?",
                    (row['id'],)
                )
                return dict(row)
        return None

    @staticmethod
    def mark_completed(task_id):
        """Marks a task as successfully completed."""
        logger.info(f"Task {task_id} completed.")
        with db_manager.get_connection() as conn:
            conn.execute(
                "UPDATE task_queue SET status = 'completed' WHERE id = ?",
                (task_id,)
            )

    @staticmethod
    def mark_failed(task_id, error_message):
        """Increments retry count and marks task as pending/failed."""
        logger.error(f"Task {task_id} failed: {error_message}")
        with db_manager.get_connection() as conn:
            row = conn.execute(
                "SELECT retry_count FROM task_queue WHERE id = ?",
                (task_id,)
            ).fetchone()
            
            if row:
                new_retry_count = row['retry_count'] + 1
                if new_retry_count < Config.MAX_RETRIES:
                    status = 'pending'
                    logger.info(f"Task {task_id} will be retried (Attempt {new_retry_count+1}/{Config.MAX_RETRIES})")
                else:
                    status = 'failed'
                    logger.warning(f"Task {task_id} failed after maximum retries.")
                
                conn.execute(
                    "UPDATE task_queue SET status = ?, retry_count = ?, error_log = ? WHERE id = ?",
                    (status, new_retry_count, str(error_message), task_id)
                )

    @staticmethod
    def recover_stalled_tasks():
        """
        Resets any tasks stuck in 'processing' state to 'pending' on system startup.
        This handles cases where the system crashed while processing.
        """
        with db_manager.get_connection() as conn:
            # OPTION 1: Simple Reset (Assuming single worker)
            cursor = conn.execute(
                "UPDATE task_queue SET status = 'pending' WHERE status = 'processing'"
            )
            if cursor.rowcount > 0:
                logger.warning(f"Recovered {cursor.rowcount} stalled tasks (reset to pending).")

# Global helper instance
task_queue = TaskQueue()
