from pydantic import BaseModel, ConfigDict
from backend.app.models.enums import UserRole

class UserBase(BaseModel):
    username: str
    role: UserRole
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str