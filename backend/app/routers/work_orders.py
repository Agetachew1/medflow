from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel

from backend.app.dependencies import get_current_user, get_db, require_role
from backend.app.models.work_order import WorkOrder
from backend.app.models.equipment import Equipment
from backend.app.models.user import User
from backend.app.models.enums import UserRole, WorkOrderPriority, WorkOrderStatus

router = APIRouter(prefix="/work-orders", tags=["work-orders"])

class DiscrepancyRead(BaseModel):
    work_order_id: int
    title: str
    equipment_hospital_id: int | None
    technician_hospital_id: int | None
    class Config: from_attributes = True

class StatusUpdate(BaseModel):
    status: WorkOrderStatus

@router.get("/discrepancies", response_model=List[DiscrepancyRead])
async def list_colocation_discrepancies(
    # Change type from WorkOrderPriority to str to prevent the 422 block
    priority: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    statement = (
        select(
            WorkOrder.id.label("work_order_id"),
            WorkOrder.title,
            Equipment.facility_id.label("equipment_hospital_id"),
            User.hospital_id.label("technician_hospital_id"),
        )
        .join(Equipment, Equipment.id == WorkOrder.equipment_id)
        .join(User, User.id == WorkOrder.technician_id)
        .where(Equipment.facility_id != User.hospital_id)
    )

    # Safely handle the string matching regardless of uppercase/lowercase
    if priority and priority.lower() != "all":
        matched_enum = next((p for p in WorkOrderPriority if p.value.lower() == priority.lower()), None)
        if matched_enum:
            statement = statement.where(WorkOrder.priority == matched_enum)

    result = await db.execute(statement.order_by(WorkOrder.id))
    return [dict(row) for row in result.mappings().all()]

@router.get("/mine")
async def list_my_work_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.FIELD_TECHNICIAN)),
):
    statement = (
        select(
            WorkOrder.id.label("id"),
            WorkOrder.title,
            WorkOrder.priority,
            WorkOrder.status,
            Equipment.serial_number,
            Equipment.model,
        )
        .join(Equipment, Equipment.id == WorkOrder.equipment_id)
        .where(WorkOrder.technician_id == current_user.id)
        .order_by(WorkOrder.id)
    )
    result = await db.execute(statement)
    return [dict(row) for row in result.mappings().all()]

@router.patch("/{work_order_id}/status")
async def update_work_order_status(
    work_order_id: int,
    payload: StatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.CLINICAL_ADMIN, UserRole.FIELD_TECHNICIAN)
    ),
):
    work_order = await db.get(WorkOrder, work_order_id)
    if work_order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work Order not found")

    if (
        current_user.role == UserRole.FIELD_TECHNICIAN
        and work_order.technician_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Technicians can only update their own work orders",
        )
        
    if payload.status == WorkOrderStatus.COMPLETED:
        work_order.mark_completed()
    elif payload.status == WorkOrderStatus.FAILED:
        work_order.mark_failed()
    else:
        work_order.status = payload.status

    await db.commit()
    await db.refresh(work_order)
    return work_order

@router.get("/reliability")
async def get_reliability_metrics(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    completed_count = func.sum(
        case((WorkOrder.status == WorkOrderStatus.COMPLETED, 1), else_=0)
    )
    failed_count = func.sum(
        case((WorkOrder.status == WorkOrderStatus.FAILED, 1), else_=0)
    )
    statement = (
        select(
            Equipment.model,
            func.count(WorkOrder.id).label("total"),
            completed_count.label("completed_count"),
            failed_count.label("failed_count"),
        )
        .join(WorkOrder, WorkOrder.equipment_id == Equipment.id)
        .group_by(Equipment.model)
        .order_by(Equipment.model)
    )
    result = await db.execute(statement)
    metrics = []
    for row in result.mappings():
        outcome_count = row["completed_count"] + row["failed_count"]
        metrics.append(
            {
                "model": row["model"],
                "total": row["total"],
                "total_work_orders": row["total"],
                "completed_count": row["completed_count"],
                "failed_count": row["failed_count"],
                "completion_ratio": (
                    row["completed_count"] / outcome_count if outcome_count else None
                ),
            }
        )
    return metrics