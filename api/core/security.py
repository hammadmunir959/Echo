from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
import os

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# In a real app, use a DB or Hash Vault.
# For now, we allow setting via ENV, defaulting to "echo_secret_key" for dev.
VALID_API_KEYS = {os.getenv("ECHO_API_KEY", "echo_secret_key")}

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key in VALID_API_KEYS:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials"
    )
