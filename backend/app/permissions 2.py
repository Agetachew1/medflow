from enum import Enum

from backend.app.models.enums import UserRole


class Permission(str, Enum):
    IDENTITY_READ = "identity:read"
    ASSET_READ = "asset:read"
    ASSET_READ_DETAIL = "asset:read_detail"
    ASSET_WRITE = "asset:write"
    JOB_READ = "job:read"
    JOB_READ_ASSIGNED = "job:read_assigned"
    JOB_WRITE = "job:write"
    JOB_CHANGE_STATUS = "job:change_status"
    REPORT_READ = "report:read"
    REPORT_UPLOAD = "report:upload"
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_ADVANCED_READ = "analytics:advanced_read"
    AUDIT_READ = "audit:read"
    USERS_MANAGE = "users:manage"
    HOSPITAL_READ = "hospital:read"
    HOSPITAL_READ_DETAIL = "hospital:read_detail"
    HOSPITAL_WRITE = "hospital:write"
    ROLES_READ = "roles:read"
    HEALTH_DETAIL_READ = "health:detail_read"
    RECORDS_INACTIVE_READ = "records:inactive_read"
    RECORDS_RESTORE = "records:restore"


ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.CLINICAL_ADMIN: frozenset(Permission) - {Permission.JOB_READ_ASSIGNED},
    UserRole.FIELD_TECHNICIAN: frozenset(
        {
            Permission.IDENTITY_READ,
            Permission.ASSET_READ,
            Permission.JOB_READ_ASSIGNED,
            Permission.JOB_CHANGE_STATUS,
            Permission.REPORT_READ,
            Permission.REPORT_UPLOAD,
            Permission.ANALYTICS_READ,
            Permission.HOSPITAL_READ,
            Permission.AUDIT_READ,
        }
    ),
    UserRole.AUDITOR: frozenset(
        {
            Permission.IDENTITY_READ,
            Permission.ASSET_READ,
            Permission.ASSET_READ_DETAIL,
            Permission.JOB_READ,
            Permission.REPORT_READ,
            Permission.ANALYTICS_READ,
            Permission.HOSPITAL_READ,
            Permission.AUDIT_READ,
        }
    ),
}


def user_has_permission(user: object, permission: Permission) -> bool:
    role = getattr(user, "role", None)
    return isinstance(role, UserRole) and permission in ROLE_PERMISSIONS[role]
