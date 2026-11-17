"""
Phase 1 Foundation Test Suite
Validates SQLite database initialization, health check, system telemetry, and project CRUD.
"""
import pytest
from starlette.testclient import TestClient
from backend.app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "ClipForge"

def test_system_status_telemetry(client):
    response = client.get("/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "gpu" in data
    assert "ram" in data
    assert "disk" in data
    assert "encoders" in data
    assert "h264_nvenc" in data["encoders"]

def test_project_lifecycle(client):
    # 1. Create project
    create_payload = {
        "title": "Phase 1 Foundation Verification Video",
        "instructions": "Find 3 clips between 30 and 60 seconds with strong hooks"
    }
    create_res = client.post("/projects", json=create_payload)
    assert create_res.status_code == 201
    project = create_res.json()
    project_id = project["id"]
    assert project["title"] == create_payload["title"]
    assert project["status"] == "created"
    
    # 2. Get project by ID
    get_res = client.get(f"/projects/{project_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == project_id
    
    # 3. List projects
    list_res = client.get("/projects")
    assert list_res.status_code == 200
    items = list_res.json()["projects"]
    assert any(p["id"] == project_id for p in items)
    
    # 4. Delete project
    del_res = client.delete(f"/projects/{project_id}")
    assert del_res.status_code == 204
    
    # 5. Verify deleted
    not_found_res = client.get(f"/projects/{project_id}")
    assert not_found_res.status_code == 404
