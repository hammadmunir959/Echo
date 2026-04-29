import structlog
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.models.dbmodels import Transcript

logger = structlog.get_logger("transcripts_service")

class TranscriptsService:
    @staticmethod
    def get_by_org(session: Session, org_id: str, limit: int = 50):
        stmt = select(Transcript).where(Transcript.organization_id == org_id).order_by(desc(Transcript.id)).limit(limit)
        return session.execute(stmt).scalars().all()

    @staticmethod
    def get_by_station(session: Session, org_id: str, station_id: str, limit: int = 50):
        stmt = select(Transcript).where(
            Transcript.organization_id == org_id,
            Transcript.station_id == station_id
        ).order_by(desc(Transcript.id)).limit(limit)
        return session.execute(stmt).scalars().all()

    @staticmethod
    def get_by_node(session: Session, org_id: str, node_id: str, limit: int = 50):
        stmt = select(Transcript).where(
            Transcript.organization_id == org_id,
            Transcript.node_id == node_id
        ).order_by(desc(Transcript.id)).limit(limit)
        return session.execute(stmt).scalars().all()

    @staticmethod
    def search(session: Session, org_id: str, query: str, limit: int = 5):
        # Fuzzy match using ILIKE
        stmt = select(Transcript).where(
            Transcript.organization_id == org_id,
            Transcript.raw_text.ilike(f"%{query}%")
        ).order_by(desc(Transcript.id)).limit(limit)
        return session.execute(stmt).scalars().all()
