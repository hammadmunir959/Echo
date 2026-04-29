from fastapi import Depends, Security, HTTPException, status, Header
from fastapi.security import APIKeyHeader
from app.core.config import get_settings, Settings
from app.db.database import get_db_session

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(
    api_key: str = Security(api_key_header),
    settings: Settings = Depends(get_settings)
):
    if api_key == settings.api_key:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

def get_organization_id(
    x_organization_id: str = Header(..., description="Organization ID mapping the tenant ruleset"),
    _ = Depends(verify_api_key)
) -> str:
    if not x_organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Organization-ID header missing"
        )
    return x_organization_id
