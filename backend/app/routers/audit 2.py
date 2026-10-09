from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db, require_permission
from backend.app.models.audit_entry import AuditEntry
from backend.app.models.equipment import Equipment
from backend.app.models.user import User
from backend.app.models.work_order import WorkOrder
from backend.app.permissions import Permission, user_has_permission
from backend.app.schemas.audit import AuditEntryRead

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/{record_type}/{record_id}", response_model=list[AuditEntryRead])
async def get_record_history(
    record_type: Literal["asset", "job"],
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.AUDIT_READ)),
) -> list[AuditEntryRead]:
    if record_type == "asset":
        record = await db.get(Equipment, record_id)
        can_read = user_has_permission(current_user, Permission.ASSET_READ)
    else:
        record = await db.get(WorkOrder, record_id)
        can_read = user_has_permission(current_user, Permission.JOB_READ) or (
            user_has_permission(current_user, Permission.JOB_READ_ASSIGNED)
            and record is not None
            and record.technician_id == current_user.id
        )

    if record is None or not can_read:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    if not record.is_active and not user_has_permission(
        current_user, Permission.RECORDS_INACTIVE_READ
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    result = await db.execute(
        select(AuditEntry, User.username)
        .join(User, User.id == AuditEntry.actor_id)
        .where(
            AuditEntry.record_type == record_type,
            AuditEntry.record_id == record_id,
        )
        .order_by(AuditEntry.created_at, AuditEntry.id)
    )
    return [
        AuditEntryRead(
            id=entry.id,
            record_type=entry.record_type,
            record_id=entry.record_id,
            action=entry.action,
            actor_id=entry.actor_id,
            actor_username=username,
            created_at=entry.created_at,
            changes=entry.changes,
        )
        for entry, username in result.all()
    ]
