from pydantic import BaseModel, ConfigDict
from backend.app.models.enums import UserRole

class UserBase(BaseModel):
    username: str
    role: UserRole
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class AdminUserCreate(BaseModel):
    username: str
    password: str
    role: UserRole
    hospital_id: int

class UserResponse(UserBase):
    id: int
    hospital_id: int | None = None
    
    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    role: UserRole | None = None
    hospital_id: int | None = None
    is_active: bool | None = None

class Token(BaseModel):
    access_token: str
    token_type: str