from core.task_queue import task_queue
from database.db_manager import db_manager

def test_queue():
    print("--- Testing Resilient Task Queue ---")
    
    # 1. Enqueue
    task_queue.enqueue_task("test_task", {"test": "data"})
    print("Enqueued test task.")
    
    # 2. Fetch
    task = task_queue.fetch_next_task()
    if task:
        print(f"Fetched task: {task['id']} - {task['task_type']} - Status: {task['status']}")
        
        # 3. Simulate Failure
        task_queue.mark_failed(task['id'], "Simulated failure for testing retry")
        
        # 4. Fetch again (should be pending)
        task_retry = task_queue.fetch_next_task()
        if task_retry and task_retry['id'] == task['id']:
            print(f"Retried task fetched: {task_retry['id']} - Status: {task_retry['status']}")
            
            # 5. Complete
            task_queue.mark_completed(task_retry['id'])
            print("Completed task.")
            
            # 6. Final check
            with db_manager.get_connection() as conn:
                final = conn.execute("SELECT status FROM task_queue WHERE id = ?", (task['id'],)).fetchone()
                print(f"Final DB Status: {final['status']}")
                
                if final['status'] == 'completed':
                    print("Queue Persistence & Logic Test: PASSED")
                else:
                    print("Queue Persistence & Logic Test: FAILED")
        else:
            print("Retry Fetch FAILED")
    else:
        print("Initial Fetch FAILED")

if __name__ == "__main__":
    test_queue()
