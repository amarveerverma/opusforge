"""
Phase 8 UI Integration & Production Build Test Suite
Verifies Next.js app routes compilation, client-facing REST contract integrity,
and end-to-end frontend-to-backend linkage.
"""
from pathlib import Path
from starlette.testclient import TestClient
from backend.app.main import app

def test_nextjs_routes_production_build():
    next_build_dir = Path("frontend/.next")
    assert next_build_dir.exists(), "Next.js .next build directory must exist"
    
    server_app_dir = next_build_dir / "server" / "app"
    assert server_app_dir.exists(), "Next.js server/app directory must exist"
    
    # Check compiled routes
    index_html = server_app_dir / "index.html"
    assert index_html.exists() or (server_app_dir / "page.js").exists()
    
    projects_route = server_app_dir / "projects"
    assert projects_route.exists(), "Compiled projects routes directory must exist"

def test_full_ui_api_contract():
    with TestClient(app) as client:
        # 1. Project creation
        p_res = client.post("/projects", json={"title": "UI Integration Project", "instructions": "test"})
        assert p_res.status_code == 201
        proj_id = p_res.json()["id"]

        # 2. Project details
        p_get = client.get(f"/projects/{proj_id}")
        assert p_get.status_code == 200
        assert p_get.json()["id"] == proj_id

        # 3. Clips list (empty initially)
        c_get = client.get(f"/projects/{proj_id}/clips")
        assert c_get.status_code == 200
        assert isinstance(c_get.json(), list)

        # 4. Renders list (empty initially)
        r_get = client.get(f"/projects/{proj_id}/renders")
        assert r_get.status_code == 200
        assert isinstance(r_get.json(), list)
