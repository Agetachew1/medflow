from pydantic import BaseModel, ConfigDict
from datetime import datetime

class ServiceReportBase(BaseModel):
    work_order_id: int
    file_url: str
    notes: str | None = None

class ServiceReportCreate(ServiceReportBase):
    pass

class ServiceReportResponse(ServiceReportBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)