from typing import Literal
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, HTTPException, Response, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel

from backend.app.dependencies import get_db, require_permission
from backend.app.models.work_order import WorkOrder
from backend.app.models.equipment import Equipment
from backend.app.models.user import User
from backend.app.models.enums import WorkOrderPriority, WorkOrderStatus
from backend.app.permissions import Permission, user_has_permission
from backend.app.models.service_report import ServiceReport
from backend.app.schemas.work_order import WorkOrderCreate, WorkOrderResponse, WorkOrderUpdate
from backend.app.schemas.page import Page
from backend.app.services.audit import audit_snapshot, commit_audited_change

router = APIRouter(prefix="/work-orders", tags=["work-orders"])
WORK_ORDER_NOT_FOUND = "Work Order not found"

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
    _: User = Depends(require_permission(Permission.ANALYTICS_READ)),
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
        .where(
            WorkOrder.is_active.is_(True),
            Equipment.is_active.is_(True),
            Equipment.facility_id != User.hospital_id,
        )
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
    current_user: User = Depends(require_permission(Permission.JOB_READ_ASSIGNED)),
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
        .where(
            WorkOrder.technician_id == current_user.id,
            WorkOrder.is_active.is_(True),
        )
        .order_by(WorkOrder.id)
    )
    result = await db.execute(statement)
    return [dict(row) for row in result.mappings().all()]

@router.patch("/{work_order_id}/status")
async def update_work_order_status(
    work_order_id: int,
    payload: StatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.JOB_CHANGE_STATUS)),
):
    work_order = await db.get(WorkOrder, work_order_id)
    if work_order is None or not work_order.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=WORK_ORDER_NOT_FOUND)

    if (
        not user_has_permission(current_user, Permission.JOB_READ)
        and work_order.technician_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Users without {Permission.JOB_READ.value} can only update "
                "their assigned work orders"
            ),
        )
        
    before = audit_snapshot(work_order, ["status"])
    if payload.status == WorkOrderStatus.COMPLETED:
        work_order.mark_completed()
    elif payload.status == WorkOrderStatus.FAILED:
        work_order.mark_failed()
    else:
        work_order.status = payload.status

    await commit_audited_change(
        db,
        record=work_order,
        record_type="job",
        action="status_change",
        actor=current_user,
        changes={"before": before, "after": audit_snapshot(work_order, ["status"])},
    )
    await db.refresh(work_order)
    return work_order

@router.get("/reliability")
async def get_reliability_metrics(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.ANALYTICS_READ)),
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
        .where(WorkOrder.is_active.is_(True), Equipment.is_active.is_(True))
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


@router.get("/inactive", response_model=list[WorkOrderResponse])
async def list_inactive_work_orders(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.RECORDS_INACTIVE_READ)),
):
    result = await db.execute(
        select(WorkOrder)
        .where(WorkOrder.is_active.is_(False))
        .order_by(WorkOrder.deleted_at.desc(), WorkOrder.id)
    )
    return result.scalars().all()


@router.post("/{work_order_id}/restore", response_model=WorkOrderResponse)
async def restore_work_order(
    work_order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RECORDS_RESTORE)),
):
    work_order = await db.get(WorkOrder, work_order_id)
    if work_order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=WORK_ORDER_NOT_FOUND)
    if work_order.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Work order is already active",
        )
    before = audit_snapshot(work_order, ["is_active", "deleted_at", "deleted_by"])
    work_order.is_active = True
    work_order.deleted_at = None
    work_order.deleted_by = None
    await commit_audited_change(
        db,
        record=work_order,
        record_type="job",
        action="restore",
        actor=current_user,
        changes={
            "before": before,
            "after": audit_snapshot(work_order, ["is_active", "deleted_at", "deleted_by"]),
        },
    )
    await db.refresh(work_order)
    return work_order


@router.get("", response_model=Page[WorkOrderResponse])
async def list_work_orders(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=25, ge=1, le=100),
    status_filter: WorkOrderStatus | None = Query(default=None, alias="status"),
    site_id: int | None = Query(default=None, ge=1),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    sort_by: Literal["id", "title", "status", "priority", "site_id"] = "id",
    sort_dir: Literal["asc", "desc"] = "asc",
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.JOB_READ)),
):
    filters = [WorkOrder.is_active.is_(True)]
    if status_filter is not None:
        filters.append(WorkOrder.status == status_filter)
    if site_id is not None:
        filters.append(Equipment.facility_id == site_id)
    if search is not None:
        search_term = f"%{search.strip()}%"
        filters.append(
            WorkOrder.title.ilike(search_term)
            | Equipment.model.ilike(search_term)
            | Equipment.serial_number.ilike(search_term)
        )

    sortable_columns = {
        "id": WorkOrder.id,
        "title": WorkOrder.title,
        "status": WorkOrder.status,
        "priority": WorkOrder.priority,
        "site_id": Equipment.facility_id,
    }
    sort_column = sortable_columns[sort_by]
    order_by = sort_column.desc() if sort_dir == "desc" else sort_column.asc()
    row_statement = (
        select(WorkOrder)
        .join(Equipment, Equipment.id == WorkOrder.equipment_id)
        .where(*filters)
        .order_by(order_by, WorkOrder.id.asc())
        .limit(size)
        .offset((page - 1) * size)
    )
    count_statement = (
        select(func.count(WorkOrder.id))
        .join(Equipment, Equipment.id == WorkOrder.equipment_id)
        .where(*filters)
    )

    result = await db.execute(row_statement)
    count_result = await db.execute(count_statement)
    return {"items": result.scalars().all(), "total": count_result.scalar_one()}

@router.post(
    "",
    response_model=WorkOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_work_order(
    payload: WorkOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.JOB_WRITE)),
):
    equipment = await db.get(Equipment, payload.equipment_id)
    if equipment is None or not equipment.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active equipment not found",
        )

    technician = await db.get(User, payload.technician_id)
    if technician is None or not technician.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Technician not found")
    if not user_has_permission(technician, Permission.JOB_READ_ASSIGNED):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Assigned user must have the field_technician role",
        )

    work_order = WorkOrder(**payload.model_dump(), is_active=True)
    db.add(work_order)
    await commit_audited_change(
        db,
        record=work_order,
        record_type="job",
        action="create",
        actor=current_user,
        changes={
            "before": None,
            "after": {
                "title": work_order.title,
                "priority": work_order.priority.value,
                "status": work_order.status.value,
                "equipment_id": work_order.equipment_id,
                "technician_id": work_order.technician_id,
                "is_active": work_order.is_active,
            },
        },
    )
    await db.refresh(work_order)
    return work_order

@router.patch("/{work_order_id}", response_model=WorkOrderResponse)
async def update_work_order(
    work_order_id: int,
    payload: WorkOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.JOB_WRITE)),
):
    work_order = await db.get(WorkOrder, work_order_id)
    if work_order is None or not work_order.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=WORK_ORDER_NOT_FOUND)

    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    technician_id = changes.get("technician_id")
    if technician_id is not None:
        technician = await db.get(User, technician_id)
        if technician is None or not technician.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Technician not found")
        if not user_has_permission(technician, Permission.JOB_READ_ASSIGNED):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Assigned user must have the field_technician role",
            )

    before = audit_snapshot(work_order, list(changes))
    for field, value in changes.items():
        setattr(work_order, field, value)

    await commit_audited_change(
        db,
        record=work_order,
        record_type="job",
        action="update",
        actor=current_user,
        changes={"before": before, "after": audit_snapshot(work_order, list(changes))},
    )
    await db.refresh(work_order)
    return work_order

@router.delete("/{work_order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work_order(
    work_order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.JOB_WRITE)),
):
    work_order = await db.get(WorkOrder, work_order_id)
    if work_order is None or not work_order.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=WORK_ORDER_NOT_FOUND)

    report_id = await db.scalar(
        select(ServiceReport.id)
        .where(ServiceReport.work_order_id == work_order_id)
        .limit(1)
    )
    if report_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Work order cannot be deleted while service reports are attached",
        )

    before = audit_snapshot(work_order, ["is_active", "deleted_at", "deleted_by"])
    work_order.is_active = False
    work_order.deleted_at = datetime.now(timezone.utc)
    work_order.deleted_by = current_user.id
    await commit_audited_change(
        db,
        record=work_order,
        record_type="job",
        action="delete",
        actor=current_user,
        changes={
            "before": before,
            "after": audit_snapshot(work_order, ["is_active", "deleted_at", "deleted_by"]),
        },
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)