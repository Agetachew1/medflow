from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import hashlib

from backend.app.dependencies import get_db, require_role
from backend.app.models.user import User
from backend.app.models.enums import UserRole

router = APIRouter(prefix="/users", tags=["users"])

class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole
    hospital_id: int

@router.post("/")
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN))
):
    existing_user = await db.execute(select(User).where(User.username == payload.username))
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    hashed_pw = hashlib.sha256(payload.password.encode()).hexdigest()

    new_user = User(
        username=payload.username,
        hashed_password=hashed_pw,
        role=payload.role,
        hospital_id=payload.hospital_id
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return {"message": f"User {new_user.username} created successfully."}