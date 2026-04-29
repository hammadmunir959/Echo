import asyncio
import json
import structlog
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Optional
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import func

from app.core.config import Settings
from app.db.database import SessionLocal
from app.models.dbmodels import Organization, Station, Node, Transcript
from app.services.transcription_service import TranscriptionService
from app.utils.event_bus import event_bus

logger = structlog.get_logger("pipeline")

class TranscriptionJob(NamedTuple):
    node_id: str
    organization_id: str
    station_id: str
    received_at: datetime
    recorded_at: Optional[datetime]
    audio_path: Path

async def pipeline_worker(
    queue: asyncio.Queue,
    settings: Settings,
    transcription_service: TranscriptionService
):
    loop = asyncio.get_event_loop()
    logger.info("Pipeline worker started")

    while True:
        job: TranscriptionJob = await queue.get()
        logger.info("Processing transcription job", 
                    node_id=job.node_id, 
                    org_id=job.organization_id, 
                    station_id=job.station_id)

        try:
            # CPU-bound transcription
            result = await loop.run_in_executor(
                None, 
                transcription_service.transcribe, 
                str(settings.audio_dir / job.audio_path)
            )

            with SessionLocal() as session:
                # Ensure Hierarchy exists
                stmt_org = pg_insert(Organization).values(
                    id=job.organization_id,
                    name=f"Org {job.organization_id}"
                ).on_conflict_do_nothing(index_elements=['id'])
                session.execute(stmt_org)

                stmt_station = pg_insert(Station).values(
                    id=job.station_id,
                    organization_id=job.organization_id,
                    name=f"Station {job.station_id}"
                ).on_conflict_do_nothing(index_elements=['id'])
                session.execute(stmt_station)

                stmt_node = pg_insert(Node).values(
                    id=job.node_id,
                    organization_id=job.organization_id,
                    station_id=job.station_id
                ).on_conflict_do_update(
                    index_elements=['id'],
                    set_={
                        'organization_id': pg_insert(Node).excluded.organization_id,
                        'station_id': pg_insert(Node).excluded.station_id,
                        'last_seen_at': func.now()
                    }
                )
                session.execute(stmt_node)

                # Persist transcript
                transcript = Transcript(
                    node_id=job.node_id,
                    organization_id=job.organization_id,
                    station_id=job.station_id,
                    received_at=job.received_at,
                    recorded_at=job.recorded_at,
                    duration_seconds=result.duration,
                    raw_text=result.text,
                    segments_json=json.dumps(result.segments),
                    audio_path=str(job.audio_path),
                    language=result.language,
                    language_probability=result.language_probability
                )
                session.add(transcript)
                session.commit()
                transcript_id = transcript.id

            # Broadcast
            await event_bus.publish({
                "type": "transcript",
                "id": transcript_id,
                "node_id": job.node_id,
                "organization_id": job.organization_id,
                "station_id": job.station_id,
                "received_at": job.received_at.isoformat(),
                "text": result.text,
                "audio_path": str(job.audio_path)
            })

            logger.info("Completed transcription job", 
                        node_id=job.node_id, 
                        transcript_id=transcript_id)

        except Exception as e:
            logger.error("Error in transcription pipeline", 
                        node_id=job.node_id, 
                        error=str(e), 
                        exc_info=True)
        finally:
            queue.task_done()
