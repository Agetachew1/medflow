from pydantic import BaseModel, ConfigDict
from backend.app.models.enums import WorkOrderPriority, WorkOrderStatus

class WorkOrderBase(BaseModel):
    title: str
    priority: WorkOrderPriority
    status: WorkOrderStatus
    equipment_id: int
    technician_id: int

class WorkOrderCreate(WorkOrderBase):
    pass

class WorkOrderResponse(WorkOrderBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)
    
class DiscrepancyRead(BaseModel):
    work_order_id: int
    title: str
    equipment_hospital_id: int | None
    technician_hospital_id: int | None

    class Config:
        from_attributes = True