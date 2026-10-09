import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import OperationalError

from backend.app.main import app
from backend.app.dependencies import get_current_user, get_db, require_permission
from backend.app.models.enums import UserRole
from backend.app.permissions import Permission, ROLE_PERMISSIONS
from backend.app.models.refresh_token import RefreshToken
from backend.app.models.equipment import Equipment
from backend.app.models.work_order import WorkOrder
from backend.app.routers.auth import (
    _token_hash,
    logout,
    refresh_access_token,
)
from backend.app.routers.audit import router as audit_router
from backend.app.schemas.user import RefreshTokenRequest
from backend.app.security import (
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from backend.app.schemas.equipment import EquipmentCreate

# This creates a virtual browser to test your API without actually starting a live server
client = TestClient(app)


class FakeSession:
    def __init__(self, error=None):
        self.error = error
        self.statements = []

    async def execute(self, statement):
        self.statements.append(str(statement))
        if self.error:
            raise self.error
        return None


class FakePagedResult:
    def __init__(self, rows=None, total=0):
        self.rows = rows or []
        self.total = total

    def mappings(self):
        return self

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one(self):
        return self.total


class FakePagedSession:
    def __init__(self, rows=None, total=0):
        self.rows = rows or []
        self.total = total
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        if len(self.statements) == 1:
            return FakePagedResult(rows=self.rows)
        return FakePagedResult(total=self.total)


class FakeRefreshResult:
    def __init__(self, scalar=None, rows=None):
        self.scalar = scalar
        self.rows = rows or []

    def scalar_one_or_none(self):
        return self.scalar

    def scalars(self):
        return self

    def all(self):
        return self.rows


class FakeRefreshSession:
    def __init__(self, token_record, user=None, chain_records=None):
        self.token_record = token_record
        self.user = user
        self.chain_records = chain_records or [token_record]
        self.statements = []
        self.added = []
        self.commit_count = 0

    async def execute(self, statement):
        self.statements.append(statement)
        where_clause = str(statement.whereclause)
        if "token_hash" in where_clause:
            return FakeRefreshResult(scalar=self.token_record)
        if "chain_id" in where_clause:
            return FakeRefreshResult(rows=self.chain_records)
        if self.user is not None:
            return FakeRefreshResult(scalar=self.user)
        return FakeRefreshResult()

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.commit_count += 1


class FakeWriteSession:
    def __init__(self, objects=None, rows=None, scalar_results=None):
        self.objects = objects or {}
        self.rows = rows or []
        self.scalar_results = list(scalar_results or [])
        self.statements = []
        self.added = []
        self.commit_count = 0
        self.next_id = 1000

    async def get(self, model, record_id):
        return self.objects.get((model, record_id))

    async def scalar(self, statement):
        self.statements.append(statement)
        if self.scalar_results:
            return self.scalar_results.pop(0)
        return None

    async def execute(self, statement):
        self.statements.append(statement)
        return FakePagedResult(rows=self.rows)

    async def flush(self):
        for value in self.added:
            if getattr(value, "id", None) is None:
                value.id = self.next_id
                self.next_id += 1
        return None

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.commit_count += 1

    async def refresh(self, record):
        return record


def override_db(session):
    async def get_fake_db():
        yield session

    app.dependency_overrides[get_db] = get_fake_db


def clear_dependency_overrides():
    app.dependency_overrides.clear()


EXPECTED_ROLE_PERMISSIONS = {
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
    UserRole.HOSPITAL_MANAGER: frozenset(
        {
            Permission.IDENTITY_READ,
            Permission.ASSET_READ,
            Permission.REPORT_READ,
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


def override_admin():
    async def get_admin():
        return SimpleNamespace(id=1, role=UserRole.CLINICAL_ADMIN)

    app.dependency_overrides[get_current_user] = get_admin


@pytest.mark.parametrize("role", list(UserRole))
def test_permission_dependency_preserves_role_access_matrix(role):
    assert ROLE_PERMISSIONS[role] == EXPECTED_ROLE_PERMISSIONS[role]
    user = SimpleNamespace(role=role)

    async def verify_each_permission():
        for permission in Permission:
            permission_checker = require_permission(permission)
            if permission in EXPECTED_ROLE_PERMISSIONS[role]:
                assert await permission_checker(current_user=user) is user
            else:
                with pytest.raises(HTTPException) as error:
                    await permission_checker(current_user=user)
                assert error.value.status_code == status.HTTP_403_FORBIDDEN
                assert error.value.detail == f"Missing required permission: {permission.value}"

    asyncio.run(verify_each_permission())


def test_identity_endpoint_returns_current_role_permissions():
    async def get_technician():
        return SimpleNamespace(username="tech", role=UserRole.FIELD_TECHNICIAN)

    app.dependency_overrides[get_current_user] = get_technician
    try:
        response = client.get("/auth/me")
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["sub"] == "tech"
    assert response.json()["permissions"] == sorted(
        permission.value for permission in EXPECTED_ROLE_PERMISSIONS[UserRole.FIELD_TECHNICIAN]
    )


def test_roles_endpoint_is_admin_only_and_lists_role_permissions():
    async def get_manager():
        return SimpleNamespace(role=UserRole.HOSPITAL_MANAGER)

    app.dependency_overrides[get_current_user] = get_manager
    try:
        forbidden = client.get("/roles")
    finally:
        clear_dependency_overrides()
    assert forbidden.status_code == status.HTTP_403_FORBIDDEN
    assert forbidden.json()["detail"] == "Missing required permission: roles:read"

    override_admin()
    try:
        response = client.get("/roles")
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_200_OK
    returned_roles = {
        item["role"]: set(item["permissions"]) for item in response.json()
    }
    assert returned_roles == {
        role.value: {permission.value for permission in permissions}
        for role, permissions in EXPECTED_ROLE_PERMISSIONS.items()
    }


@pytest.mark.parametrize("role", list(UserRole))
def test_all_existing_roles_can_read_equipment(role):
    async def get_role_user():
        return SimpleNamespace(id=1, role=role)

    app.dependency_overrides[get_current_user] = get_role_user
    override_db(FakePagedSession())
    try:
        response = client.get("/equipment")
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [
        (UserRole.CLINICAL_ADMIN, status.HTTP_403_FORBIDDEN),
        (UserRole.FIELD_TECHNICIAN, status.HTTP_200_OK),
        (UserRole.HOSPITAL_MANAGER, status.HTTP_403_FORBIDDEN),
    ],
)
def test_assigned_work_order_endpoint_preserves_existing_access(role, expected_status):
    async def get_role_user():
        return SimpleNamespace(id=1, role=role)

    app.dependency_overrides[get_current_user] = get_role_user
    override_db(FakePagedSession())
    try:
        response = client.get("/work-orders/mine")
    finally:
        clear_dependency_overrides()

    assert response.status_code == expected_status


def test_user_management_requires_users_manage_permission():
    async def get_manager():
        return SimpleNamespace(id=1, role=UserRole.HOSPITAL_MANAGER)

    app.dependency_overrides[get_current_user] = get_manager
    try:
        response = client.get("/users")
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Missing required permission: users:manage"


def make_refresh_token(user_id=1, expires_delta=None):
    token = create_refresh_token(
        {"sub": "refresh-user"},
        token_id="test-token-id",
        expires_delta=expires_delta or timedelta(days=7),
    )
    expires_at = datetime.now(timezone.utc) + (expires_delta or timedelta(days=7))
    record = RefreshToken(
        user_id=user_id,
        token_hash=_token_hash(token),
        chain_id="test-chain",
        issued_at=datetime.now(timezone.utc),
        expires_at=expires_at,
        revoked=False,
    )
    return token, record


def test_refresh_rotates_valid_token_and_keeps_access_subject():
    token, record = make_refresh_token()
    user = SimpleNamespace(id=1, username="refresh-user", role=UserRole.CLINICAL_ADMIN, is_active=True)
    db = FakeRefreshSession(record, user=user)
    response = asyncio.run(refresh_access_token(RefreshTokenRequest(refresh_token=token), db))

    assert response.token_type == "bearer"
    assert decode_access_token(response.access_token)["sub"] == "refresh-user"
    replacement_claims = decode_refresh_token(response.refresh_token)
    assert replacement_claims["sub"] == "refresh-user"
    assert len(db.added[0].token_hash) == 64
    assert db.added[0].token_hash != response.refresh_token
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(response.refresh_token)
    assert record.revoked is True
    assert db.commit_count == 1
    assert len(db.added) == 1
    assert db.added[0].chain_id == record.chain_id
    assert db.added[0].token_hash == _token_hash(response.refresh_token)


def test_login_returns_access_and_refresh_tokens(monkeypatch):
    from backend.app.routers import auth as auth_router_module

    user = SimpleNamespace(
        id=1,
        username="refresh-user",
        role=UserRole.CLINICAL_ADMIN,
        is_active=True,
        hashed_password="hashed",
    )
    db = FakeRefreshSession(token_record=None, user=user)
    monkeypatch.setattr(auth_router_module, "verify_password", lambda *_: True)
    override_db(db)
    try:
        response = client.post(
            "/auth/token",
            data={"username": "refresh-user", "password": "password"},
        )
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]
    assert response.json()["refresh_token"]
    assert len(db.added) == 1
    assert db.added[0].token_hash == _token_hash(response.json()["refresh_token"])


def test_refresh_endpoint_does_not_require_access_token():
    token, record = make_refresh_token()
    user = SimpleNamespace(id=1, username="refresh-user", role=UserRole.CLINICAL_ADMIN, is_active=True)
    override_db(FakeRefreshSession(record, user=user))
    try:
        response = client.post("/auth/refresh", json={"refresh_token": token})
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["access_token"]
    assert response.json()["refresh_token"] != token


def test_expired_refresh_token_is_rejected():
    token, record = make_refresh_token(expires_delta=timedelta(seconds=-1))
    db = FakeRefreshSession(record)

    with pytest.raises(HTTPException) as error:
        asyncio.run(refresh_access_token(RefreshTokenRequest(refresh_token=token), db))

    assert error.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert db.added == []


def test_reused_refresh_token_revokes_every_token_in_chain():
    token, used_record = make_refresh_token()
    used_record.revoked = True
    later_record = RefreshToken(
        user_id=1,
        token_hash="a" * 64,
        chain_id=used_record.chain_id,
        issued_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=3),
        revoked=False,
    )
    db = FakeRefreshSession(
        used_record,
        chain_records=[used_record, later_record],
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(refresh_access_token(RefreshTokenRequest(refresh_token=token), db))

    assert error.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert used_record.revoked is True
    assert later_record.revoked is True
    assert db.commit_count == 1


def test_logout_revokes_refresh_and_later_refresh_is_rejected():
    token, record = make_refresh_token(expires_delta=timedelta(days=7))
    db = FakeRefreshSession(record)

    response = asyncio.run(logout(RefreshTokenRequest(refresh_token=token), db))
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert record.revoked is True
    assert db.commit_count == 1

    with pytest.raises(HTTPException) as error:
        asyncio.run(refresh_access_token(RefreshTokenRequest(refresh_token=token), db))

    assert error.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_equipment_delete_is_soft_and_audited():
    equipment = SimpleNamespace(
        id=8,
        is_active=True,
        deleted_at=None,
        deleted_by=None,
    )
    db = FakeWriteSession(objects={(Equipment, 8): equipment})
    override_admin()
    override_db(db)
    try:
        response = client.delete("/equipment/8")
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert equipment.is_active is False
    assert equipment.deleted_at is not None
    assert equipment.deleted_by == 1
    audit_entry = next(item for item in db.added if item.__class__.__name__ == "AuditEntry")
    assert (audit_entry.record_type, audit_entry.record_id, audit_entry.action) == ("asset", 8, "delete")
    assert audit_entry.actor_id == 1
    assert db.commit_count == 1


def test_inactive_equipment_list_filters_in_sql():
    inactive = SimpleNamespace(
        id=8,
        serial_number="MRI-008",
        model="MRI",
        status="offline",
        charge_level=0,
        facility_id=1,
        is_active=False,
        deleted_at=datetime.now(timezone.utc),
        deleted_by=1,
    )
    db = FakeWriteSession(rows=[inactive])
    override_admin()
    override_db(db)
    try:
        response = client.get("/equipment/inactive")
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_200_OK
    assert response.json()[0]["is_active"] is False
    assert "equipments.is_active IS false" in str(db.statements[0])


def test_equipment_restore_is_audited():
    equipment = SimpleNamespace(
        id=8,
        serial_number="MRI-008",
        model="MRI",
        status="offline",
        charge_level=0,
        facility_id=1,
        is_active=False,
        deleted_at=datetime.now(timezone.utc),
        deleted_by=2,
    )
    db = FakeWriteSession(objects={(Equipment, 8): equipment})
    override_admin()
    override_db(db)
    try:
        response = client.post("/equipment/8/restore")
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_200_OK
    assert equipment.is_active is True
    assert equipment.deleted_at is None
    assert equipment.deleted_by is None
    entry = next(item for item in db.added if item.__class__.__name__ == "AuditEntry")
    assert entry.action == "restore"
    assert entry.changes["before"]["is_active"] is False
    assert entry.changes["after"]["is_active"] is True
    assert db.commit_count == 1


def test_work_order_status_change_writes_audit_in_same_commit():
    work_order = SimpleNamespace(
        id=14,
        is_active=True,
        technician_id=5,
        status="pending",
        mark_completed=lambda: None,
        mark_failed=lambda: None,
    )
    user = SimpleNamespace(id=1, role=UserRole.CLINICAL_ADMIN)

    async def get_admin_user():
        return user

    db = FakeWriteSession(objects={(WorkOrder, 14): work_order})
    app.dependency_overrides[get_current_user] = get_admin_user
    override_db(db)
    try:
        response = client.patch(
            "/work-orders/14/status",
            json={"status": "in_progress"},
        )
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_200_OK
    entry = next(item for item in db.added if item.__class__.__name__ == "AuditEntry")
    assert entry.action == "status_change"
    assert entry.changes == {
        "before": {"status": "pending"},
        "after": {"status": "in_progress"},
    }
    assert entry.actor_id == user.id
    assert db.commit_count == 1


def test_soft_deleted_work_order_keeps_its_row_and_references():
    work_order = SimpleNamespace(
        id=14,
        is_active=True,
        deleted_at=None,
        deleted_by=None,
    )
    db = FakeWriteSession(objects={(WorkOrder, 14): work_order})
    override_admin()
    override_db(db)
    try:
        response = client.delete("/work-orders/14")
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert work_order.is_active is False
    assert work_order.deleted_by == 1
    assert not any(isinstance(item, WorkOrder) for item in db.added)
    entry = next(item for item in db.added if item.__class__.__name__ == "AuditEntry")
    assert entry.action == "delete"
    assert db.commit_count == 1


def test_work_order_list_filters_inactive_rows_in_sql():
    db = FakePagedSession()
    override_admin()
    override_db(db)
    try:
        response = client.get("/work-orders")
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_200_OK
    assert "work_orders.is_active is true" in str(db.statements[0]).lower()
    assert "work_orders.is_active is true" in str(db.statements[1]).lower()


def test_inactive_work_order_restore_is_audited():
    work_order = SimpleNamespace(
        id=14,
        title="Repair pump",
        priority="low",
        status="pending",
        equipment_id=3,
        technician_id=5,
        is_active=False,
        deleted_at=datetime.now(timezone.utc),
        deleted_by=2,
    )
    db = FakeWriteSession(objects={(WorkOrder, 14): work_order})
    override_admin()
    override_db(db)
    try:
        response = client.post("/work-orders/14/restore")
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["is_active"] is True
    assert work_order.deleted_at is None
    assert work_order.deleted_by is None
    entry = next(item for item in db.added if item.__class__.__name__ == "AuditEntry")
    assert entry.record_type == "job"
    assert entry.action == "restore"
    assert db.commit_count == 1


def test_non_admin_cannot_list_or_restore_inactive_records():
    async def get_manager():
        return SimpleNamespace(id=2, role=UserRole.HOSPITAL_MANAGER)

    app.dependency_overrides[get_current_user] = get_manager
    try:
        list_response = client.get("/equipment/inactive")
        restore_response = client.post("/equipment/8/restore")
    finally:
        clear_dependency_overrides()

    assert list_response.status_code == status.HTTP_403_FORBIDDEN
    assert restore_response.status_code == status.HTTP_403_FORBIDDEN


def test_audit_history_is_chronological_and_record_scoped():
    first_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    entries = [
        (
            SimpleNamespace(
                id=1,
                record_type="asset",
                record_id=8,
                action="create",
                actor_id=1,
                created_at=first_time,
                changes={"before": None, "after": {"model": "MRI"}},
            ),
            "admin",
        )
    ]
    equipment = SimpleNamespace(id=8, is_active=True)
    user = SimpleNamespace(id=2, role=UserRole.HOSPITAL_MANAGER)
    db = FakeWriteSession(objects={(Equipment, 8): equipment}, rows=entries)

    async def get_manager():
        return user

    app.dependency_overrides[get_current_user] = get_manager
    override_db(db)
    try:
        response = client.get("/audit/asset/8")
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_200_OK
    assert response.json()[0]["actor_username"] == "admin"
    assert response.json()[0]["changes"]["after"]["model"] == "MRI"
    query = str(db.statements[0])
    assert "audit_entries.record_type" in query
    assert "audit_entries.record_id" in query
    assert "audit_entries.created_at" in query


def test_technician_can_read_assigned_job_history_only():
    work_order = SimpleNamespace(id=14, technician_id=5, is_active=True)
    entry = (
        SimpleNamespace(
            id=1,
            record_type="job",
            record_id=14,
            action="status_change",
            actor_id=5,
            created_at=datetime.now(timezone.utc),
            changes={"before": {"status": "pending"}, "after": {"status": "completed"}},
        ),
        "tech",
    )
    user = SimpleNamespace(id=5, role=UserRole.FIELD_TECHNICIAN)

    async def get_technician():
        return user

    db = FakeWriteSession(objects={(WorkOrder, 14): work_order}, rows=[entry])
    app.dependency_overrides[get_current_user] = get_technician
    override_db(db)
    try:
        allowed = client.get("/audit/job/14")
        denied = client.get("/audit/job/15")
    finally:
        clear_dependency_overrides()

    assert allowed.status_code == status.HTTP_200_OK
    assert denied.status_code == status.HTTP_404_NOT_FOUND


def test_auditor_can_read_active_asset_and_job_history():
    asset = SimpleNamespace(id=8, is_active=True)
    work_order = SimpleNamespace(id=14, technician_id=999, is_active=True)
    user = SimpleNamespace(id=7, role=UserRole.AUDITOR)

    async def get_auditor():
        return user

    db = FakeWriteSession(
        objects={(Equipment, 8): asset, (WorkOrder, 14): work_order},
        rows=[],
    )
    app.dependency_overrides[get_current_user] = get_auditor
    override_db(db)
    try:
        asset_history = client.get("/audit/asset/8")
        job_history = client.get("/audit/job/14")
    finally:
        clear_dependency_overrides()

    assert asset_history.status_code == status.HTTP_200_OK
    assert job_history.status_code == status.HTTP_200_OK


def test_equipment_update_audits_changed_fields():
    equipment = SimpleNamespace(
        id=8,
        serial_number="MRI-008",
        model="MRI",
        status="available",
        charge_level=80,
        facility_id=1,
        is_active=True,
        deleted_at=None,
        deleted_by=None,
    )
    db = FakeWriteSession(objects={(Equipment, 8): equipment})
    override_admin()
    override_db(db)
    try:
        response = client.patch("/equipment/8", json={"model": "MRI-X"})
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_200_OK
    entry = next(item for item in db.added if item.__class__.__name__ == "AuditEntry")
    assert entry.action == "update"
    assert entry.changes == {
        "before": {"model": "MRI"},
        "after": {"model": "MRI-X"},
    }
    assert db.commit_count == 1


def test_work_order_update_audits_changed_fields():
    work_order = SimpleNamespace(
        id=14,
        title="Repair pump",
        priority="low",
        status="pending",
        equipment_id=3,
        technician_id=5,
        is_active=True,
        deleted_at=None,
        deleted_by=None,
    )
    db = FakeWriteSession(objects={(WorkOrder, 14): work_order})
    override_admin()
    override_db(db)
    try:
        response = client.patch("/work-orders/14", json={"title": "Repair pump motor"})
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_200_OK
    entry = next(item for item in db.added if item.__class__.__name__ == "AuditEntry")
    assert entry.action == "update"
    assert entry.changes["before"] == {"title": "Repair pump"}
    assert entry.changes["after"] == {"title": "Repair pump motor"}
    assert db.commit_count == 1


def test_work_order_create_writes_audit():
    from backend.app.models.user import User

    equipment = SimpleNamespace(id=3, is_active=True)
    technician = SimpleNamespace(id=5, is_active=True, role=UserRole.FIELD_TECHNICIAN)
    db = FakeWriteSession(
        objects={(Equipment, 3): equipment, (User, 5): technician}
    )
    override_admin()
    override_db(db)
    try:
        response = client.post(
            "/work-orders",
            json={
                "title": "Repair pump",
                "priority": "low",
                "status": "pending",
                "equipment_id": 3,
                "technician_id": 5,
            },
        )
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_201_CREATED
    entry = next(item for item in db.added if item.__class__.__name__ == "AuditEntry")
    assert entry.record_type == "job"
    assert entry.action == "create"
    assert entry.changes["before"] is None
    assert entry.changes["after"]["title"] == "Repair pump"
    assert db.commit_count == 1


def test_equipment_create_writes_audit():
    db = FakeWriteSession(scalar_results=[None, 1])
    override_admin()
    override_db(db)
    try:
        response = client.post(
            "/equipment",
            json={
                "serial_number": "AUDIT-MRI-1",
                "model": "MRI",
                "status": "ACTIVE",
                "charge_level": 90,
                "facility_id": 1,
            },
        )
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_201_CREATED
    entry = next(item for item in db.added if item.__class__.__name__ == "AuditEntry")
    assert entry.record_type == "asset"
    assert entry.action == "create"
    assert entry.changes["before"] is None
    assert entry.changes["after"]["serial_number"] == "AUDIT-MRI-1"
    assert db.commit_count == 1


def test_rejected_asset_update_writes_no_audit_entry():
    equipment = SimpleNamespace(
        id=8,
        serial_number="MRI-008",
        model="MRI",
        status="available",
        charge_level=80,
        facility_id=1,
        is_active=True,
        deleted_at=None,
        deleted_by=None,
    )
    db = FakeWriteSession(objects={(Equipment, 8): equipment})
    override_admin()
    override_db(db)
    try:
        response = client.patch("/equipment/8", json={"facility_id": 999})
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert db.added == []
    assert db.commit_count == 0


def test_audit_routes_have_no_mutation_methods():
    audit_routes = list(audit_router.routes)

    assert audit_routes
    assert all(route.methods == {"GET"} for route in audit_routes)


def compiled_sql(statement):
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    ).lower().replace("%%", "%")


def test_equipment_create_schema_accepts_frontend_payload():
    payload = EquipmentCreate(
        serial_number="TEST-EQUIPMENT-001",
        model="Test Model",
        status="ACTIVE",
        charge_level=85,
        facility_id=1,
        hospital_id=1,
    )

    assert payload.status == "ACTIVE"
    assert payload.facility_id == 1

def test_equipment_create_schema_accepts_legacy_hospital_id():
    payload = EquipmentCreate(
        serial_number="TEST-EQUIPMENT-002",
        model="Test Model",
        status="MAINTENANCE",
        charge_level=85,
        hospital_id=2,
    )

    assert payload.facility_id == 2

def test_api_is_running():
    """Proves the FastAPI server boots up and generates documentation"""
    response = client.get("/docs")
    assert response.status_code == 200

def test_security_blocks_unauthorized_users():
    """Proves the Command Center strictly enforces login requirements"""
    response = client.get("/equipment/")
    
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}

def test_health_endpoint_does_not_require_database():
    async def unexpected_db_access():
        raise AssertionError("Liveness check must not access the database")

    app.dependency_overrides[get_db] = unexpected_db_access
    try:
        response = client.get("/health")
    finally:
        clear_dependency_overrides()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint_reports_database_available():
    session = FakeSession()
    override_db(session)
    try:
        response = client.get("/health/ready")
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ready"}
    assert session.statements == ["SELECT 1"]


def test_readiness_endpoint_reports_database_unavailable():
    session = FakeSession(OperationalError("SELECT 1", {}, OSError("database unavailable")))
    override_db(session)
    try:
        response = client.get("/health/ready")
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {
        "status": "not_ready",
        "dependencies": {"database": "unavailable"},
    }
    assert "database unavailable" not in response.text


def test_health_detail_requires_admin():
    response = client.get("/health/detail")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_health_detail_forbids_non_admin():
    async def get_manager():
        return SimpleNamespace(role=UserRole.HOSPITAL_MANAGER)

    app.dependency_overrides[get_current_user] = get_manager
    try:
        response = client.get("/health/detail")
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_health_detail_reports_each_dependency_for_admin(monkeypatch):
    session = FakeSession()
    override_db(session)

    async def get_admin():
        return SimpleNamespace(role=UserRole.CLINICAL_ADMIN)

    async def s3_available():
        return "ok"

    app.dependency_overrides[get_current_user] = get_admin
    monkeypatch.setattr("backend.app.main._s3_health", s3_available)
    try:
        response = client.get("/health/detail")
    finally:
        clear_dependency_overrides()

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "ok",
        "dependencies": {"database": "ok", "s3": "ok"},
    }


def test_version_endpoint():
    response = client.get("/version")

    assert response.status_code == 200

def test_my_work_orders_requires_authentication():
    response = client.get("/work-orders/mine")

    assert response.status_code == 401

def test_maintenance_flags_requires_authentication():
    response = client.get("/hospitals/maintenance-flags")

    assert response.status_code == 401

def test_service_reports_requires_authentication():
    response = client.get("/service-reports/")

    assert response.status_code == 401

def test_invalid_bearer_token_is_rejected():
    response = client.get(
        "/equipment/",
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 401


def test_equipment_list_returns_requested_page_and_total():
    session = FakePagedSession(
        rows=[{
            "id": 21,
            "serial_number": "MRI-021",
            "model": "MRI",
            "charge_level": 80,
            "status": "available",
            "hospital_id": 2,
        }],
        total=21,
    )
    override_admin()
    override_db(session)
    try:
        response = client.get("/equipment", params={"page": 3, "size": 10})
    finally:
        clear_dependency_overrides()

    assert response.status_code == 200
    assert response.json()["total"] == 21
    assert response.json()["items"][0]["id"] == 21
    sql = compiled_sql(session.statements[0])
    assert "limit 10 offset 20" in sql
    assert "order by equipments.id asc" in sql
    assert "limit" not in compiled_sql(session.statements[1])


def test_equipment_list_combines_filters_and_sorts_descending():
    session = FakePagedSession(total=1)
    override_admin()
    override_db(session)
    try:
        response = client.get(
            "/equipment",
            params={
                "status": "available",
                "site_id": 2,
                "search": "MRI",
                "sort_by": "model",
                "sort_dir": "desc",
            },
        )
    finally:
        clear_dependency_overrides()

    assert response.status_code == 200
    assert response.json()["total"] == 1
    for statement in session.statements:
        sql = compiled_sql(statement)
        assert "equipments.status = 'available'" in sql
        assert "equipments.facility_id = 2" in sql
        assert "equipments.model ilike '%mri%'" in sql
        assert "equipments.serial_number ilike '%mri%'" in sql
    assert "order by equipments.model desc" in compiled_sql(session.statements[0])


def test_equipment_list_rejects_invalid_sort_and_oversized_page():
    override_admin()
    try:
        invalid_sort = client.get("/equipment", params={"sort_by": "not_a_column"})
        oversized_page = client.get("/equipment", params={"size": 101})
    finally:
        clear_dependency_overrides()

    assert invalid_sort.status_code == 422
    assert oversized_page.status_code == 422


def test_work_order_list_paginates_filters_and_sorts_in_sql():
    session = FakePagedSession(total=4)
    override_admin()
    override_db(session)
    try:
        response = client.get(
            "/work-orders",
            params={
                "page": 2,
                "size": 2,
                "status": "in_progress",
                "site_id": 3,
                "search": "sensor",
                "sort_by": "title",
                "sort_dir": "desc",
            },
        )
    finally:
        clear_dependency_overrides()

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 4}
    for statement in session.statements:
        sql = compiled_sql(statement)
        assert "work_orders.status = 'in_progress'" in sql
        assert "equipments.facility_id = 3" in sql
        assert "work_orders.title ilike '%sensor%'" in sql
        assert "equipments.model ilike '%sensor%'" in sql
        assert "equipments.serial_number ilike '%sensor%'" in sql
        assert "join equipments" in sql
    assert "limit 2 offset 2" in compiled_sql(session.statements[0])
    assert "order by work_orders.title desc" in compiled_sql(session.statements[0])


def test_work_order_list_still_requires_admin_authentication():
    response = client.get("/work-orders")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED