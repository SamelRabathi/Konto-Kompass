from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from konto_models import User, TenantMembership
from .db import get_db
from .settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, settings.app_secret, algorithm=settings.jwt_algorithm)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nicht authentifiziert")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.app_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ungültiges Token") from exc

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Benutzer nicht gefunden")
    return user


ROLE_RANK = {"viewer": 1, "member": 2, "owner": 3}


def _check_membership(
    tenant_id: int,
    user: User,
    db: Session,
    min_role: str,
) -> TenantMembership:
    membership = (
        db.query(TenantMembership)
        .filter(TenantMembership.tenant_id == tenant_id, TenantMembership.user_id == user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kein Zugriff auf diesen Tenant")
    if ROLE_RANK.get(membership.role, 0) < ROLE_RANK.get(min_role, 0):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unzureichende Berechtigung")
    return membership


def require_tenant_access(
    tenant_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenantMembership:
    return _check_membership(tenant_id, user, db, "viewer")


def require_tenant_member(
    tenant_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenantMembership:
    return _check_membership(tenant_id, user, db, "member")
