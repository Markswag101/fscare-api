"""
Authentication utilities — JWT tokens + password hashing.
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db, Hospital

SECRET_KEY  = os.getenv("SECRET_KEY", "fscare-secret-change-in-production-2026")
ALGORITHM   = "HS256"
TOKEN_EXPIRY_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer      = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
):
    """Returns {"role": "admin"} or {"role": "hospital", "hospital": <Hospital>}"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


def require_admin(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def require_hospital(user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user.get("role") != "hospital":
        raise HTTPException(status_code=403, detail="Hospital access required")
    hospital = db.query(Hospital).filter(Hospital.id == user.get("hospital_id")).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    if not hospital.approved:
        raise HTTPException(status_code=403, detail="Hospital account pending approval")
    return hospital
