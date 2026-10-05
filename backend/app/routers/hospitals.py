from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_current_user, get_db, require_role
from backend.app.models.hospital import Hospital
from backend.app.models.equipment import Equipment
from backend.app.models.user import User
from backend.app.models.work_order import WorkOrder
from backend.app.models.enums import EquipmentStatus, UserRole, WorkOrderStatus

router = APIRouter(prefix="/hospitals", tags=["hospitals"])

@router.get("/maintenance-flags")
async def get_maintenance_flags(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
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
        .join(Equipment, Equipment.facility_id == Hospital.id)
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
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN))
):
    # This query perfectly counts technicians who report to this supervisor AND have pending work orders
    statement = (
        select(func.count(func.distinct(User.id)))
        .join(Hospital, Hospital.id == User.hospital_id)
        .join(WorkOrder, WorkOrder.technician_id == User.id)
        .where(Hospital.supervisor_id == supervisor_id)
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