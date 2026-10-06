from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.schemas.equipment import EquipmentCreate

# This creates a virtual browser to test your API without actually starting a live server
client = TestClient(app)

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

def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

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