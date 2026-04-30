"""Auth: register, login, current user."""
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.common.audit import AuditService
from app.common.models import User
from app.core.base import BaseRepository, BaseService
from app.core.database import db_session
from app.core.errors import AppError
from app.core.security import (
    create_access_token, decode_token, hash_password, verify_password,
)


# ─── Schemas ──────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email:     EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password:  str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    expires_at:   datetime


class UserOut(BaseModel):
    id:        UUID
    email:     EmailStr
    full_name: str
    is_admin:  bool
    is_active: bool

    class Config:
        from_attributes = True


# ─── Repository ───────────────────────────────────────────────────────────────
class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        return self.find_by(email=email.lower())


# ─── Service ──────────────────────────────────────────────────────────────────
class AuthService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)
        self.users = UserRepository(db)
        self.audit = AuditService(db)

    def register(self, data: RegisterRequest, *, ip: str | None = None) -> User:
        if self.users.get_by_email(data.email):
            raise AppError("CDP-AUT-0005", context={"email": data.email})

        user = User(
            email=data.email.lower(),
            full_name=data.full_name.strip(),
            password_hash=hash_password(data.password),
        )
        self.users.create(user)
        self.audit.record(
            action="USER_REGISTERED",
            entity_type="USER",
            entity_id=user.id,
            actor_id=user.id,
            actor_email=user.email,
            after_state={"email": user.email, "full_name": user.full_name},
            metadata={"ip": ip},
        )
        return user

    def login(self, data: LoginRequest, *, ip: str | None = None, user_agent: str | None = None) -> tuple[User, TokenResponse]:
        user = self.users.get_by_email(data.email)
        if not user or not verify_password(data.password, user.password_hash):
            self.audit.record(
                action="USER_LOGIN_FAILED",
                entity_type="USER",
                entity_id=data.email,
                actor_email=data.email,
                metadata={"ip": ip, "reason": "invalid_credentials"},
            )
            raise AppError("CDP-AUT-0001")
        if not user.is_active:
            raise AppError("CDP-AUT-0004")

        user.last_login_at = datetime.now(timezone.utc)
        self.audit.record_activity(
            user_id=user.id,
            activity_type="LOGIN",
            ip_address=ip,
            user_agent=user_agent,
        )
        self.audit.record(
            action="USER_LOGIN",
            entity_type="USER",
            entity_id=user.id,
            actor_id=user.id,
            actor_email=user.email,
            metadata={"ip": ip},
        )

        token = create_access_token(
            subject=str(user.id),
            claims={"email": user.email, "is_admin": user.is_admin},
        )
        decoded = decode_token(token)
        return user, TokenResponse(
            access_token=token,
            expires_at=datetime.fromtimestamp(decoded["exp"], tz=timezone.utc),
        )


# ─── FastAPI dependencies ─────────────────────────────────────────────────────
_bearer = HTTPBearer(auto_error=False)


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else None)


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db:    Annotated[Session, Depends(db_session)],
) -> User:
    if creds is None:
        raise AppError("CDP-AUT-0006")
    payload = decode_token(creds.credentials)
    user = db.get(User, UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise AppError("CDP-AUT-0004")
    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if not user.is_admin:
        raise AppError("CDP-ACC-0035")
    return user


# ─── Router ───────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(
    data:    RegisterRequest,
    request: Request,
    db:      Annotated[Session, Depends(db_session)],
):
    svc = AuthService(db)
    user = svc.register(data, ip=_client_ip(request))
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    data:    LoginRequest,
    request: Request,
    db:      Annotated[Session, Depends(db_session)],
):
    svc = AuthService(db)
    _, token = svc.login(
        data,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return token


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]):
    return user
