from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db, require_permission
from backend.app.models.hospital import Hospital
from backend.app.models.equipment import Equipment
from backend.app.models.user import User
from backend.app.models.work_order import WorkOrder
from backend.app.models.enums import EquipmentStatus, WorkOrderStatus
from backend.app.permissions import Permission
from backend.app.schemas.hospital import HospitalCreate, HospitalResponse, HospitalUpdate

router = APIRouter(prefix="/hospitals", tags=["hospitals"])
HOSPITAL_NOT_FOUND = "Hospital not found"

@router.get("/maintenance-flags")
async def get_maintenance_flags(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.ANALYTICS_READ)),
):
    maintenance_count = func.sum(
        case(
            (
                Equipment.status == EquipmentStatus.UNDER_MAINTENANCE,
                1,
            ),
            else_=0,
        )
    )
    statement = (
        select(
            Hospital.id.label("hospital_id"),
            Hospital.name,
            func.count(Equipment.id).label("total_equipment"),
            maintenance_count.label("maintenance_count"),
        )
        .join(
            Equipment,
            (Equipment.facility_id == Hospital.id) & Equipment.is_active.is_(True),
        )
        .group_by(Hospital.id, Hospital.name)
        .having(
            maintenance_count * 1.0 / func.count(Equipment.id) > 0.3
        )
        .order_by(Hospital.id)
    )
    result = await db.execute(statement)
    return [dict(row) for row in result.mappings().all()]

@router.get("/supervisors/{supervisor_id}/reporting-lines")
async def get_reporting_lines(
    supervisor_id: int, 
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.ANALYTICS_ADVANCED_READ))
):
    # This query perfectly counts technicians who report to this supervisor AND have pending work orders
    statement = (
        select(func.count(func.distinct(User.id)))
        .join(Hospital, Hospital.id == User.hospital_id)
        .join(WorkOrder, WorkOrder.technician_id == User.id)
        .join(Equipment, Equipment.id == WorkOrder.equipment_id)
        .where(Hospital.supervisor_id == supervisor_id)
        .where(WorkOrder.is_active.is_(True), Equipment.is_active.is_(True))
        .where(
            WorkOrder.status.in_(
                [WorkOrderStatus.PENDING, WorkOrderStatus.IN_PROGRESS]
            )
        )
    )
    
    result = await db.execute(statement)
    count = result.scalar() or 0
    
    return {
        "supervisor_id": supervisor_id,
        "technicians_with_active_work_orders": count
    }

@router.get("", response_model=list[HospitalResponse])
async def list_hospitals(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.HOSPITAL_READ)),
):
    result = await db.execute(select(Hospital).order_by(Hospital.id))
    return result.scalars().all()

@router.get("/{hospital_id}", response_model=HospitalResponse)
async def get_hospital(
    hospital_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.HOSPITAL_READ_DETAIL)),
):
    hospital = await db.get(Hospital, hospital_id)
    if hospital is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=HOSPITAL_NOT_FOUND)
    return hospital

@router.post(
    "",
    response_model=HospitalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_hospital(
    payload: HospitalCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.HOSPITAL_WRITE)),
):
    hospital = Hospital(**payload.model_dump())
    db.add(hospital)
    await db.commit()
    await db.refresh(hospital)
    return hospital

@router.patch("/{hospital_id}", response_model=HospitalResponse)
async def update_hospital(
    hospital_id: int,
    payload: HospitalUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.HOSPITAL_WRITE)),
):
    hospital = await db.get(Hospital, hospital_id)
    if hospital is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=HOSPITAL_NOT_FOUND)

    for field, value in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(hospital, field, value)

    await db.commit()
    await db.refresh(hospital)
    return hospital

@router.delete("/{hospital_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hospital(
    hospital_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.HOSPITAL_WRITE)),
):
    hospital = await db.get(Hospital, hospital_id)
    if hospital is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=HOSPITAL_NOT_FOUND)

    equipment_id = await db.scalar(
        select(Equipment.id).where(Equipment.facility_id == hospital_id).limit(1)
    )
    if equipment_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hospital cannot be deleted while it has equipment",
        )

    assigned_user_id = await db.scalar(
        select(User.id).where(User.hospital_id == hospital_id).limit(1)
    )
    if assigned_user_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hospital cannot be deleted while users are assigned to it",
        )

    await db.delete(hospital)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)