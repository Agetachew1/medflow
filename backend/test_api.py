from fastapi.testclient import TestClient
from backend.app.main import app

# This creates a virtual browser to test your API without actually starting a live server
client = TestClient(app)

def test_api_is_running():
    """Proves the FastAPI server boots up and generates documentation"""
    response = client.get("/docs")
    assert response.status_code == 200

def test_security_blocks_unauthorized_users():
    """Proves the Command Center strictly enforces login requirements"""
    response = client.get("/equipment/")
    
    # We expect a 401 Unauthorized status because we didn't send a login token
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}