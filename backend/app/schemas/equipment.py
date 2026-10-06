from pydantic import BaseModel, Field, ConfigDict, model_validator
from backend.app.models.enums import EquipmentStatus

class EquipmentBase(BaseModel):
    serial_number: str
    model: str
    status: EquipmentStatus
    charge_level: float = Field(..., ge=0.0, le=100.0)
    facility_id: int


class EquipmentCreate(EquipmentBase):
    status: str = EquipmentStatus.AVAILABLE.value
    facility_id: int | None = None
    hospital_id: int | None = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def map_hospital_id_to_facility_id(self):
        if self.facility_id is None:
            self.facility_id = self.hospital_id
        if self.facility_id is None:
            raise ValueError("facility_id or hospital_id is required")
        return self

class EquipmentUpdate(BaseModel):
    model: str | None = None
    status: EquipmentStatus | None = None
    charge_level: float | None = Field(default=None, ge=0.0, le=100.0)
    facility_id: int | None = None

class EquipmentResponse(EquipmentBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
    
