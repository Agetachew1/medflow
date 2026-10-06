from pydantic import BaseModel, ConfigDict

class HospitalBase(BaseModel):
    name: str
    location_region: str
    capacity: int
    supervisor_id: int

class HospitalCreate(HospitalBase):
    pass

class HospitalUpdate(BaseModel):
    name: str | None = None
    location_region: str | None = None
    capacity: int | None = None
    supervisor_id: int | None = None

class HospitalResponse(HospitalBase):
    id: int
    
    # Reads data directly from the SQLAlchemy ORM model
    model_config = ConfigDict(from_attributes=True)