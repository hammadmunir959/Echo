from celery import Celery
import os
from core.config import Config

# Initialize Celery
# Broker: Redis (default port 6379)
# Result Backend: Redis 
app = Celery(
    'echo',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    include=['core.distributed_tasks']
)

# Optional configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300, # 5 minutes max per task
)

if __name__ == '__main__':
    app.start()
