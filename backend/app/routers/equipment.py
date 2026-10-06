from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any, Dict

from backend.app.dependencies import get_current_user, get_db, require_role
from backend.app.models.equipment import Equipment
from backend.app.models.hospital import Hospital
from backend.app.models.user import User
from backend.app.models.enums import UserRole, EquipmentStatus
from backend.app.schemas.equipment import EquipmentCreate, EquipmentResponse, EquipmentUpdate

router = APIRouter(prefix="/equipment", tags=["equipment"])
EQUIPMENT_NOT_FOUND = "Equipment not found"

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
        )
        .where(Equipment.is_active.is_(True))
        .order_by(Equipment.id)
    )
    return [dict(row) for row in result.mappings().all()]

@router.post("/", status_code=status.HTTP_201_CREATED)
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
    _: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    statement = (
        select(
            Equipment.id,
            Equipment.serial_number,
            Equipment.model,
            Equipment.charge_level,
            Hospital.name.label("hospital"),
        )
        .join(Hospital, Hospital.id == Equipment.facility_id)
        .where(Equipment.is_active == True)
        .where(Equipment.charge_level < 20)
        .order_by(Equipment.charge_level)
    )
    
    result = await db.execute(statement)
    return [dict(row) for row in result.mappings().all()]

@router.get("/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(
    equipment_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN)),
):
    equipment = await db.get(Equipment, equipment_id)
    if equipment is None or not equipment.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=EQUIPMENT_NOT_FOUND)
    return equipment

@router.patch("/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(
    equipment_id: int,
    payload: EquipmentUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN)),
):
    equipment = await db.get(Equipment, equipment_id)
    if equipment is None or not equipment.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=EQUIPMENT_NOT_FOUND)

    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    facility_id = changes.get("facility_id")
    if facility_id is not None:
        hospital_exists = await db.scalar(
            select(Hospital.id).where(Hospital.id == facility_id)
        )
        if hospital_exists is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")

    for field, value in changes.items():
        setattr(equipment, field, value)

    await db.commit()
    await db.refresh(equipment)
    return equipment

@router.delete("/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_equipment(
    equipment_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN)),
):
    equipment = await db.get(Equipment, equipment_id)
    if equipment is None or not equipment.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=EQUIPMENT_NOT_FOUND)

    equipment.is_active = False
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
