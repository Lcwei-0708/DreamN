import logging
from passlib.context import CryptContext
from fastapi import HTTPException, Depends
from extensions.keycloak import get_keycloak
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_token(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    return credentials.credentials

async def verify_token(token: str = Depends(get_token)):
    keycloak = get_keycloak()
    try:
        is_valid = await keycloak.verify_token(token)
        if is_valid:
            return token
        raise HTTPException(status_code=401)
    except Exception:
        raise HTTPException(status_code=401)