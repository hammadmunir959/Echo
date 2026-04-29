from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.db.database import get_db_session
from app.utils.auth_utils import get_organization_id
from app.models.dbmodels import Node
from app.schemas.node import NodeOut
import structlog

logger = structlog.get_logger("api.nodes")
router = APIRouter()

@router.get("/", response_model=List[NodeOut])
def list_nodes(
    db: Session = Depends(get_db_session),
    organization_id: str = Depends(get_organization_id)
):
    stmt = select(Node).where(Node.organization_id == organization_id).order_by(desc(Node.last_seen_at))
    nodes = db.execute(stmt).scalars().all()
    
    return [
        NodeOut(
            id=n.id,
            organization_id=n.organization_id,
            station_id=n.station_id,
            label=n.label,
            last_seen_at=n.last_seen_at, # type: ignore
            transcript_count=n.transcript_count
        ) for n in nodes
    ]

@router.get("/{node_id}", response_model=NodeOut)
def get_node(
    node_id: str,
    db: Session = Depends(get_db_session),
    organization_id: str = Depends(get_organization_id)
):
    stmt = select(Node).where(Node.id == node_id, Node.organization_id == organization_id)
    n = db.execute(stmt).scalar_one_or_none()
    
    if not n:
        raise HTTPException(status_code=404, detail="Node not found")
        
    return NodeOut(
        id=n.id,
        organization_id=n.organization_id,
        station_id=n.station_id,
        label=n.label,
        last_seen_at=n.last_seen_at, # type: ignore
        transcript_count=n.transcript_count
    )
