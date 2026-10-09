from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditEntryRead(BaseModel):
    id: int
    record_type: str
    record_id: int
    action: str
    actor_id: int
    actor_username: str
    created_at: datetime
    changes: dict[str, Any]
