from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db, require_role
from backend.app.models.hospital import Hospital
from backend.app.models.user import User
from backend.app.models.enums import UserRole
from backend.app.security import hash_password
from backend.app.schemas.user import AdminUserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])
HOSPITAL_NOT_FOUND = "Hospital not found"

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Username already taken"},
        404: {"description": HOSPITAL_NOT_FOUND},
    },
)
async def create_user(
    payload: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN))
):
    existing_user = await db.execute(select(User).where(User.username == payload.username))
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

    hospital_exists = await db.scalar(
        select(Hospital.id).where(Hospital.id == payload.hospital_id)
    )
    if hospital_exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=HOSPITAL_NOT_FOUND)

    new_user = User(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        hospital_id=payload.hospital_id
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return {"message": f"User {new_user.username} created successfully."}

@router.get("", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN)),
):
    result = await db.execute(select(User).order_by(User.id))
    return result.scalars().all()

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN)),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    changes = payload.model_dump(exclude_unset=True)
    if any(changes.get(field) is None for field in ("role", "is_active") if field in changes):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="role and is_active cannot be null",
        )

    hospital_id = changes.get("hospital_id")
    if hospital_id is not None:
        hospital_exists = await db.scalar(
            select(Hospital.id).where(Hospital.id == hospital_id)
        )
        if hospital_exists is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=HOSPITAL_NOT_FOUND)

    for field, value in changes.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN)),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_active = False
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)