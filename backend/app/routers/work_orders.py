from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel

from backend.app.dependencies import get_db, require_role
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
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN)),
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

@router.patch("/{work_order_id}/status")
async def update_work_order_status(
    work_order_id: int,
    payload: StatusUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN, UserRole.FIELD_TECHNICIAN))
):
    work_order = await db.get(WorkOrder, work_order_id)
    if work_order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work Order not found")
        
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
async def get_reliability_metrics(db: AsyncSession = Depends(get_db)):
    wo_result = await db.execute(select(WorkOrder))
    work_orders = wo_result.scalars().all()
    
    eq_result = await db.execute(select(Equipment))
    equipments = {e.id: e.model for e in eq_result.scalars().all()}
    
    metrics = {}
    for wo in work_orders:
        model = equipments.get(wo.equipment_id, "Unknown Model")
        if model not in metrics:
            metrics[model] = {
                "model": model, 
                "total_work_orders": 0, 
                "completed_count": 0, 
                "failed_count": 0
            }
        
        metrics[model]["total_work_orders"] += 1
        if wo.status == WorkOrderStatus.COMPLETED:
            metrics[model]["completed_count"] += 1
        elif wo.status == WorkOrderStatus.FAILED:
            metrics[model]["failed_count"] += 1
            
    return list(metrics.values())