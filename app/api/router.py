from fastapi import APIRouter
from app.api.v1 import ingest, transcripts, nodes, stream

api_router = APIRouter()
api_router.include_router(ingest.router, prefix="/ingest", tags=["Ingest"])
api_router.include_router(transcripts.router, prefix="/transcripts", tags=["Transcripts"])
api_router.include_router(nodes.router, prefix="/nodes", tags=["Nodes"])
api_router.include_router(stream.router, prefix="/stream", tags=["Stream"])
