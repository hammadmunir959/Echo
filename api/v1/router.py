from fastapi import APIRouter
from api.v1.endpoints import control, data, stream

api_router = APIRouter()
api_router.include_router(control.router, prefix="/control", tags=["Control"])
api_router.include_router(data.router, prefix="/data", tags=["Data"])
api_router.include_router(stream.router, prefix="/stream", tags=["Stream"])
