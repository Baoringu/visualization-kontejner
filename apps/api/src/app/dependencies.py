from dataclasses import dataclass
from datetime import UTC, datetime
from secrets import compare_digest

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Membership, Organization, SessionRecord, User
from app.security import digest


@dataclass(frozen=True)
class CurrentUser:
    user: User
    organization: Organization
    role: str
    csrf_token: str


def current_user(request: Request, db: Session = Depends(get_db)) -> CurrentUser:
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_REQUIRED")
    session = db.scalar(select(SessionRecord).where(SessionRecord.token_hash == digest(token)))
    if not session or session.revoked_at or session.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_SESSION")
    user = db.get(User, session.user_id)
    organization = db.get(Organization, session.organization_id)
    membership = db.scalar(select(Membership).where(Membership.organization_id == session.organization_id, Membership.user_id == session.user_id))
    if not user or not user.is_active or not organization or not membership:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_SESSION")
    csrf = request.cookies.get(get_settings().csrf_cookie_name, "")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin != get_settings().web_origin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="INVALID_ORIGIN")
        header = request.headers.get("X-CSRF-Token", "")
        if not header or not compare_digest(header, csrf) or not compare_digest(digest(header), session.csrf_hash):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF_REQUIRED")
    return CurrentUser(user, organization, membership.role, csrf)


def require_role(*roles: str):
    def dependency(current: CurrentUser = Depends(current_user)) -> CurrentUser:
        if current.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="FORBIDDEN")
        return current

    return dependency
