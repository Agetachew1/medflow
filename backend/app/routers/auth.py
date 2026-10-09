
from datetime import datetime, timedelta, timezone
import hashlib
from uuid import uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.dependencies import get_db, require_permission
from backend.app.models.refresh_token import RefreshToken
from backend.app.models.user import User
from backend.app.permissions import Permission, ROLE_PERMISSIONS
from backend.app.schemas.role import CurrentUserRead
from backend.app.schemas.user import RefreshTokenRequest, Token, UserCreate, UserResponse
from backend.app.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _unauthorized_refresh() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _issue_refresh_token(
    db: AsyncSession, user: User, chain_id: str
) -> tuple[str, RefreshToken]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.refresh_token_expire_days)
    token_id = str(uuid4())
    token = create_refresh_token(
        {"sub": user.username},
        token_id=token_id,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )
    record = RefreshToken(
        user_id=user.id,
        token_hash=_token_hash(token),
        chain_id=chain_id,
        issued_at=now,
        expires_at=expires_at,
        revoked=False,
    )
    db.add(record)
    return token, record


async def _revoke_token_chain(db: AsyncSession, chain_id: str) -> None:
    result = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.chain_id == chain_id)
        .with_for_update()
    )
    for chain_token in result.scalars().all():
        chain_token.revoked = True
    await db.commit()


@router.get("/me", response_model=CurrentUserRead)
async def get_identity(
    current_user: User = Depends(require_permission(Permission.IDENTITY_READ)),
) -> CurrentUserRead:
    return CurrentUserRead(
        sub=current_user.username,
        role=current_user.role,
        permissions=sorted(ROLE_PERMISSIONS[current_user.role], key=lambda item: item.value),
    )


@router.post("/token")
async def login_for_access_token(
    from_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Token:
    # Find user
    result = await db.execute(select(User).where(User.username == from_data.username))
    user = result.scalar_one_or_none()

    # Verify password
    if (
        not user
        or not user.is_active
        or not verify_password(from_data.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate token
    refresh_token, _ = _issue_refresh_token(db, user, str(uuid4()))
    await db.commit()
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value}
    )
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    try:
        claims = decode_refresh_token(payload.refresh_token, verify_exp=False)
    except jwt.InvalidTokenError as exc:
        raise _unauthorized_refresh() from exc

    result = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.token_hash == _token_hash(payload.refresh_token))
        .with_for_update()
    )
    refresh_record = result.scalar_one_or_none()
    if refresh_record is None:
        raise _unauthorized_refresh()

    if refresh_record.revoked:
        await _revoke_token_chain(db, refresh_record.chain_id)
        raise _unauthorized_refresh()

    now = datetime.now(timezone.utc)
    expires_at = refresh_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if (
        claims.get("sub") is None
        or not isinstance(claims.get("exp"), (int, float))
        or claims["exp"] <= now.timestamp()
        or expires_at <= now
    ):
        raise _unauthorized_refresh()

    user_result = await db.execute(select(User).where(User.id == refresh_record.user_id))
    user = user_result.scalar_one_or_none()
    if (
        user is None
        or not user.is_active
        or user.username != claims["sub"]
    ):
        refresh_record.revoked = True
        await db.commit()
        raise _unauthorized_refresh()

    refresh_record.revoked = True
    replacement, _ = _issue_refresh_token(db, user, refresh_record.chain_id)
    await db.commit()
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value}
    )
    return Token(
        access_token=access_token,
        refresh_token=replacement,
        token_type="bearer",
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        decode_refresh_token(payload.refresh_token)
    except jwt.InvalidTokenError as exc:
        raise _unauthorized_refresh() from exc

    result = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.token_hash == _token_hash(payload.refresh_token))
        .with_for_update()
    )
    refresh_record = result.scalar_one_or_none()
    if refresh_record is None:
        raise _unauthorized_refresh()
    if refresh_record.revoked:
        await _revoke_token_chain(db, refresh_record.chain_id)
        raise _unauthorized_refresh()

    refresh_record.revoked = True
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.USERS_MANAGE)),
):
    #checking if the username already exists in the db
    ##func.lower() 
    existing = await db.execute(select(User).where(func.lower(User.username) == payload.username.lower()))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{payload.username}' is already taken",
        )

    #create a new User object with the provided username, hashed password, and role
    user = User(
        username = payload.username,
        hashed_password=hash_password(payload.password),
        role=payload.role
    )

    #add that new user object to the db
    db.add(user)
    #commit the db transaction
    await db.commit()
    #refresh the user object so that we get the id the db generated
    await db.refresh(user)
    return user