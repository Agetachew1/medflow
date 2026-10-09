from datetime import datetime, timezone
from typing import Any, Dict, List, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db, require_permission
from backend.app.models.equipment import Equipment
from backend.app.models.hospital import Hospital
from backend.app.models.user import User
from backend.app.models.enums import EquipmentStatus
from backend.app.permissions import Permission
from backend.app.schemas.equipment import EquipmentCreate, EquipmentResponse, EquipmentUpdate
from backend.app.schemas.page import Page
from backend.app.services.audit import audit_snapshot, commit_audited_change
from backend.app.services.audit import audit_value

router = APIRouter(prefix="/equipment", tags=["equipment"])
EQUIPMENT_NOT_FOUND = "Equipment not found"

@router.get("", response_model=Page[Dict[str, Any]])
async def get_all_equipment(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=25, ge=1, le=100),
    status_filter: EquipmentStatus | None = Query(default=None, alias="status"),
    site_id: int | None = Query(default=None, ge=1),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    sort_by: Literal["id", "serial_number", "model", "status", "charge_level", "site_id"] = "id",
    sort_dir: Literal["asc", "desc"] = "asc",
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.ASSET_READ))
):
    filters = [Equipment.is_active.is_(True)]
    if status_filter is not None:
        filters.append(Equipment.status == status_filter)
    if site_id is not None:
        filters.append(Equipment.facility_id == site_id)
    if search is not None:
        search_term = f"%{search.strip()}%"
        filters.append(
            Equipment.model.ilike(search_term)
            | Equipment.serial_number.ilike(search_term)
        )

    sortable_columns = {
        "id": Equipment.id,
        "serial_number": Equipment.serial_number,
        "model": Equipment.model,
        "status": Equipment.status,
        "charge_level": Equipment.charge_level,
        "site_id": Equipment.facility_id,
    }
    sort_column = sortable_columns[sort_by]
    order_by = sort_column.desc() if sort_dir == "desc" else sort_column.asc()
    row_statement = (
        select(
            Equipment.id,
            Equipment.serial_number,
            Equipment.model,
            Equipment.charge_level,
            Equipment.status,
            Equipment.facility_id.label("hospital_id"),
        )
        .where(*filters)
        .order_by(order_by, Equipment.id.asc())
        .limit(size)
        .offset((page - 1) * size)
    )
    count_statement = select(func.count(Equipment.id)).where(*filters)

    result = await db.execute(row_statement)
    count_result = await db.execute(count_statement)
    return {
        "items": [dict(row) for row in result.mappings().all()],
        "total": count_result.scalar_one(),
    }

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_equipment(
    payload: EquipmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ASSET_WRITE))
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
        await commit_audited_change(
            db,
            record=new_equip,
            record_type="asset",
            action="create",
            actor=current_user,
            changes={
                "before": None,
                "after": {
                    "serial_number": new_equip.serial_number,
                    "model": new_equip.model,
                    "charge_level": audit_value(new_equip.charge_level),
                    "status": new_equip.status.value,
                    "facility_id": new_equip.facility_id,
                    "is_active": new_equip.is_active,
                },
            },
        )
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
    _: User = Depends(require_permission(Permission.ANALYTICS_READ)),
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
        .where(Equipment.is_active.is_(True))
        .where(Equipment.charge_level < 20)
        .order_by(Equipment.charge_level)
    )
    
    result = await db.execute(statement)
    return [dict(row) for row in result.mappings().all()]

@router.get("/inactive", response_model=list[EquipmentResponse])
async def list_inactive_equipment(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.RECORDS_INACTIVE_READ)),
):
    result = await db.execute(
        select(Equipment)
        .where(Equipment.is_active.is_(False))
        .order_by(Equipment.deleted_at.desc(), Equipment.id)
    )
    return result.scalars().all()


@router.get("/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(
    equipment_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.ASSET_READ_DETAIL)),
):
    equipment = await db.get(Equipment, equipment_id)
    if equipment is None or not equipment.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=EQUIPMENT_NOT_FOUND)
    return equipment


@router.post("/{equipment_id}/restore", response_model=EquipmentResponse)
async def restore_equipment(
    equipment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RECORDS_RESTORE)),
):
    equipment = await db.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=EQUIPMENT_NOT_FOUND)
    if equipment.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Equipment is already active",
        )
    before = audit_snapshot(equipment, ["is_active", "deleted_at", "deleted_by"])
    equipment.is_active = True
    equipment.deleted_at = None
    equipment.deleted_by = None
    await commit_audited_change(
        db,
        record=equipment,
        record_type="asset",
        action="restore",
        actor=current_user,
        changes={
            "before": before,
            "after": audit_snapshot(equipment, ["is_active", "deleted_at", "deleted_by"]),
        },
    )
    await db.refresh(equipment)
    return equipment


@router.patch("/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(
    equipment_id: int,
    payload: EquipmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ASSET_WRITE)),
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

    before = audit_snapshot(equipment, list(changes))
    for field, value in changes.items():
        setattr(equipment, field, value)

    await commit_audited_change(
        db,
        record=equipment,
        record_type="asset",
        action="update",
        actor=current_user,
        changes={"before": before, "after": audit_snapshot(equipment, list(changes))},
    )
    await db.refresh(equipment)
    return equipment

@router.delete("/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_equipment(
    equipment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ASSET_WRITE)),
):
    equipment = await db.get(Equipment, equipment_id)
    if equipment is None or not equipment.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=EQUIPMENT_NOT_FOUND)

    before = audit_snapshot(equipment, ["is_active", "deleted_at", "deleted_by"])
    equipment.is_active = False
    equipment.deleted_at = datetime.now(timezone.utc)
    equipment.deleted_by = current_user.id
    await commit_audited_change(
        db,
        record=equipment,
        record_type="asset",
        action="delete",
        actor=current_user,
        changes={
            "before": before,
            "after": audit_snapshot(equipment, ["is_active", "deleted_at", "deleted_by"]),
        },
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
