from fastapi import APIRouter, Depends

from backend.app.dependencies import require_permission
from backend.app.models.user import User
from backend.app.permissions import Permission, ROLE_PERMISSIONS
from backend.app.schemas.role import RolePermissionsRead

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RolePermissionsRead])
async def list_roles(
    _: User = Depends(require_permission(Permission.ROLES_READ)),
) -> list[RolePermissionsRead]:
    return [
        RolePermissionsRead(
            role=role,
            permissions=sorted(permissions, key=lambda item: item.value),
        )
        for role, permissions in ROLE_PERMISSIONS.items()
    ]
