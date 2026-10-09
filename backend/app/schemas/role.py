from pydantic import BaseModel

from backend.app.models.enums import UserRole
from backend.app.permissions import Permission


class RolePermissionsRead(BaseModel):
    role: UserRole
    permissions: list[Permission]


class CurrentUserRead(BaseModel):
    sub: str
    role: UserRole
    permissions: list[Permission]
