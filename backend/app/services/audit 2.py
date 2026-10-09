from typing import Any
from enum import Enum
from decimal import Decimal
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_entry import AuditEntry
from backend.app.models.user import User


def audit_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def audit_snapshot(record: Any, fields: list[str]) -> dict[str, Any]:
    return {field: audit_value(getattr(record, field)) for field in fields}


async def commit_audited_change(
    db: AsyncSession,
    *,
    record: Any,
    record_type: str,
    action: str,
    actor: User,
    changes: dict[str, Any],
) -> None:
    """Commit a record change and its immutable audit entry atomically."""
    await db.flush()
    db.add(
        AuditEntry(
            record_type=record_type,
            record_id=record.id,
            action=action,
            actor_id=actor.id,
            changes=changes,
        )
    )
    await db.commit()
