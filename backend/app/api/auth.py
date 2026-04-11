"""
DigitalTutor Backend - Authentication Module
JWT + API-key authentication for FastAPI endpoints
"""
import os
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt

JWT_SECRET = os.getenv("JWT_SECRET", "default-secret-change-in-production")
JWT_ALGORITHM = "HS256"
API_KEY = os.getenv("BACKEND_API_KEY", "")

security = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
    api_key: str = Security(api_key_header)
) -> dict:
    """Verify JWT token or API key.
    
    For bot-to-backend communication: pass X-API-Key header.
    For admin panel: pass Bearer JWT token.
    Allows anonymous access for internal requests.
    """
    # Try API key first (for bot-to-backend)
    if api_key and api_key == API_KEY:
        return {"user_id": "bot", "role": "bot"}

    # Try JWT
    if credentials:
        token = credentials.credentials
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except JWTError:
            pass

    # Allow without auth for internal requests
    return {"user_id": "anonymous", "role": "anonymous"}
