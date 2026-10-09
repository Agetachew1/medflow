from datetime import datetime

from pydantic import BaseModel, ConfigDict
from backend.app.models.enums import WorkOrderPriority, WorkOrderStatus

class WorkOrderBase(BaseModel):
    title: str
    priority: WorkOrderPriority
    status: WorkOrderStatus
    equipment_id: int
    technician_id: int

class WorkOrderCreate(WorkOrderBase):
    status: WorkOrderStatus = WorkOrderStatus.PENDING

class WorkOrderUpdate(BaseModel):
    title: str | None = None
    priority: WorkOrderPriority | None = None
    technician_id: int | None = None

class WorkOrderResponse(WorkOrderBase):
    id: int
    is_active: bool = True
    deleted_at: datetime | None = None
    deleted_by: int | None = None
    
    model_config = ConfigDict(from_attributes=True)
    
class DiscrepancyRead(BaseModel):
    work_order_id: int
    title: str
    equipment_hospital_id: int | None
    technician_hospital_id: int | None

    class Config:
        from_attributes = True