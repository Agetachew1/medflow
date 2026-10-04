from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any, Dict
from pydantic import BaseModel, Field, model_validator

from backend.app.dependencies import get_db, require_role
from backend.app.models.equipment import Equipment
from backend.app.models.hospital import Hospital
from backend.app.models.user import User
from backend.app.models.enums import UserRole, EquipmentStatus

router = APIRouter(prefix="/equipment", tags=["equipment"])

class EquipmentCreate(BaseModel):
    serial_number: str
    model: str
    charge_level: int
    status: str = EquipmentStatus.AVAILABLE.value
    facility_id: int | None = None
    hospital_id: int | None = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def map_hospital_id_to_facility_id(self):
        if self.facility_id is None:
            self.facility_id = self.hospital_id
        if self.facility_id is None:
            raise ValueError("facility_id or hospital_id is required")
        return self

@router.get("/")
async def get_all_equipment(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN, UserRole.HOSPITAL_MANAGER, UserRole.FIELD_TECHNICIAN))
):
    result = await db.execute(
        select(
            Equipment.id,
            Equipment.serial_number,
            Equipment.model,
            Equipment.charge_level,
            Equipment.status,
            Equipment.facility_id.label("hospital_id"),
        ).order_by(Equipment.id)
    )
    return [dict(row) for row in result.mappings().all()]

@router.post("/")
async def create_equipment(
    payload: EquipmentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN))
):
    status_map = {
        "ACTIVE": EquipmentStatus.AVAILABLE,
        "AVAILABLE": EquipmentStatus.AVAILABLE,
        "IN_USE": EquipmentStatus.IN_USE,
        "MAINTENANCE": EquipmentStatus.UNDER_MAINTENANCE,
        "UNDER_MAINTENANCE": EquipmentStatus.UNDER_MAINTENANCE,
        "RETIRED": EquipmentStatus.OFFLINE,
        "OFFLINE": EquipmentStatus.OFFLINE,
    }
    normalized_status = status_map.get(payload.status.upper())
    if normalized_status is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported equipment status: {payload.status}",
        )

    existing_equipment = await db.scalar(
        select(Equipment).where(Equipment.serial_number == payload.serial_number)
    )
    if existing_equipment is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Equipment with serial number '{payload.serial_number}' already exists.",
        )

    hospital_exists = await db.scalar(
        select(Hospital.id).where(Hospital.id == payload.facility_id)
    )
    if hospital_exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hospital with ID {payload.facility_id} does not exist.",
        )

    new_equip = Equipment(
        serial_number=payload.serial_number,
        model=payload.model,
        charge_level=payload.charge_level,
        status=normalized_status,
        facility_id=payload.facility_id,
        is_active=True,
    )
    db.add(new_equip)
    try:
        await db.commit()
        await db.refresh(new_equip)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create equipment because a database constraint was violated.",
        ) from exc
    return new_equip

@router.get("/low-charge")
async def low_charge_alert(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN)),
) -> List[Dict[str, Any]]:
    statement = (
        select(
            Equipment.id,
            Equipment.model,
            Equipment.charge_level,
            Equipment.facility_id.label("hospital_id")
        )
        .where(Equipment.is_active == True)
        .where(Equipment.charge_level < 20)
        .order_by(Equipment.charge_level)
    )
    
    result = await db.execute(statement)
    return [dict(row) for row in result.mappings().all()]
