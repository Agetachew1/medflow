from pydantic import BaseModel, Field, ConfigDict
from backend.app.models.enums import EquipmentStatus

class EquipmentBase(BaseModel):
    serial_number: str
    model: str
    status: EquipmentStatus
    charge_level: float = Field(..., ge=0.0, le=100.0)
    facility_id: int
    
class EquipmentCreate(EquipmentBase):
    pass 

class EquipmentResponse(EquipmentBase):
    id: int
    
model_config = ConfigDict(from_attributes=True)
    
