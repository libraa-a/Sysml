import tempfile
import unittest
from pathlib import Path

try:
    from fastapi.testclient import TestClient
    from sysml_docgen.app import app
except (RuntimeError, ModuleNotFoundError):
    TestClient = None
    app = None
from sysml_docgen.config import determine_frontend_dir
from sysml_docgen.store import ModelStore


@unittest.skipIf(TestClient is None, "FastAPI TestClient requires httpx")
class FastApiAppTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_store = app.state.store
        self.original_frontend_dir = getattr(app.state, "frontend_dir", None)
        self.original_frontend_mode = getattr(app.state, "frontend_mode", None)
        app.state.store = ModelStore(Path(self.temp_dir.name) / "store.sqlite3")
        self.client = TestClient(app)
        for username, password in (("engineer", "engineer123"), ("teacher", "teacher123")):
            response = self.client.post(
                "/api/auth/register",
                json={"username": username, "password": password},
            )
            self.assertEqual(response.status_code, 200)

    def tearDown(self):
        self.client.close()
        app.state.store = self.original_store
        app.state.frontend_dir = self.original_frontend_dir
        app.state.frontend_mode = self.original_frontend_mode
        self.temp_dir.cleanup()

    def test_health_exposes_fastapi_mms_metadata(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["framework"], "fastapi")
        self.assertIn(payload["storage"], {"sqlite", "mongodb"})
        self.assertIn("MMS", payload["components"])
        self.assertEqual(payload["capabilities"]["max_model_bytes"], 10 * 1024 * 1024)
        self.assertIn(payload["capabilities"]["frontend"], {"dist", "missing", "static-fallback"})
        self.assertIn(payload["capabilities"]["frontend_ready"], {True, False})

    def test_mms_projects_route_is_compatible(self):
        response = self.client.get("/api/projects")
        self.assertEqual(response.status_code, 200)
        projects = response.json()["projects"]
        self.assertTrue(any(project["id"] == "workspace-engineer" for project in projects))

    def test_auth_login_returns_token_and_me_reads_identity(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "engineer", "password": "engineer123"},
        )
        self.assertEqual(response.status_code, 200)
        identity = response.json()["identity"]
        self.assertEqual(identity["username"], "engineer")
        self.assertEqual(identity["role"], "user")
        self.assertTrue(identity["token"])

        me = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {identity['token']}"})
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["identity"]["username"], "engineer")

    def test_auth_login_rejects_bad_password(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "engineer", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 401)

    def test_mdk_xmi_export_route_returns_xml(self):
        response = self.client.get("/api/projects/satellite-power/branches/main/export?format=xmi")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/xml", response.headers["content-type"])
        self.assertIn("<packagedElement", response.text)

    def test_docgen_pdf_route_returns_pdf(self):
        created = self.client.post(
            "/api/projects/satellite-power/branches/main/documents",
            json={"format": "pdf", "template": "# {{model:summary}}"},
        )
        self.assertEqual(created.status_code, 200)
        document_id = created.json()["document"]["id"]
        pdf = self.client.get(f"/api/projects/satellite-power/branches/main/documents/{document_id}?format=pdf")
        self.assertEqual(pdf.status_code, 200)
        self.assertIn("application/pdf", pdf.headers["content-type"])
        self.assertTrue(pdf.content.startswith(b"%PDF-"))

    def test_project_roles_block_reader_writes(self):
        self.skipTest("Role-based project access was replaced by per-user private samples.")
        response = self.client.post(
            "/api/projects/satellite-power/branches/main/elements",
            json={"id": "REQ-ROLE", "name": "权限需求", "type": "Requirement"},
            headers={"X-User": "reviewer", "X-Role": "user"},
        )
        self.assertEqual(response.status_code, 403)

    def test_project_roles_treat_unknown_user_as_reader(self):
        self.skipTest("Role-based project access was replaced by per-user private samples.")
        response = self.client.post(
            "/api/projects/satellite-power/branches/main/elements",
            json={"id": "REQ-GHOST", "name": "未知用户需求", "type": "Requirement"},
            headers={"X-User": "ghost", "X-Role": "user"},
        )
        self.assertEqual(response.status_code, 403)

    def test_each_user_gets_empty_workspace(self):
        engineer = self.client.get("/api/projects", headers={"X-User": "engineer", "X-Role": "user"})
        teacher = self.client.get("/api/projects", headers={"X-User": "teacher", "X-Role": "user"})
        self.assertEqual(engineer.status_code, 200)
        self.assertEqual(teacher.status_code, 200)

        engineer_projects = engineer.json()["projects"]
        teacher_projects = teacher.json()["projects"]
        engineer_ids = {project["id"] for project in engineer_projects}
        teacher_ids = {project["id"] for project in teacher_projects}
        self.assertIn("workspace-engineer", engineer_ids)
        self.assertIn("workspace-teacher", teacher_ids)
        self.assertNotIn("workspace-teacher", engineer_ids)
        self.assertNotIn("workspace-engineer", teacher_ids)
        self.assertTrue(all(project["elements"] == 0 for project in engineer_projects))
        self.assertTrue(all(project["elements"] == 0 for project in teacher_projects))

    def test_private_project_blocks_other_user_writes(self):
        response = self.client.post(
            "/api/projects/workspace-teacher/branches/main/elements",
            json={"id": "REQ-PRIVATE", "name": "Private requirement", "type": "Requirement"},
            headers={"X-User": "engineer", "X-Role": "user"},
        )
        self.assertEqual(response.status_code, 403)

    def test_publish_project_creates_shared_project(self):
        created = self.client.post(
            "/api/projects/workspace-engineer/branches/main/elements",
            json={"id": "REQ-SHARED", "name": "Shared requirement", "type": "Requirement"},
            headers={"X-User": "engineer", "X-Role": "user"},
        )
        self.assertEqual(created.status_code, 200)

        published = self.client.post(
            "/api/projects/workspace-engineer/publish",
            json={"id": "engineering-shared", "name": "Engineering Shared", "members": "teacher"},
            headers={"X-User": "engineer", "X-Role": "user"},
        )
        self.assertEqual(published.status_code, 200)
        project = published.json()["project"]
        self.assertEqual(project["visibility"], "shared")
        self.assertEqual(project["owner"], "engineer")

        teacher = self.client.get("/api/projects", headers={"X-User": "teacher", "X-Role": "user"})
        teacher_ids = {item["id"] for item in teacher.json()["projects"]}
        self.assertIn("engineering-shared", teacher_ids)

    def test_copy_shared_project_creates_private_workspace_copy(self):
        created = self.client.post(
            "/api/projects",
            json={"id": "team-shared", "name": "Team Shared", "members": "teacher"},
            headers={"X-User": "engineer", "X-Role": "user"},
        )
        self.assertEqual(created.status_code, 200)

        copied = self.client.post(
            "/api/projects/team-shared/copy",
            json={"id": "teacher-team-copy", "name": "Teacher Copy"},
            headers={"X-User": "teacher", "X-Role": "user"},
        )
        self.assertEqual(copied.status_code, 200)
        project = copied.json()["project"]
        self.assertEqual(project["visibility"], "private")
        self.assertEqual(project["owner"], "teacher")

        teacher = self.client.get("/api/projects", headers={"X-User": "teacher", "X-Role": "user"})
        teacher_ids = {item["id"] for item in teacher.json()["projects"]}
        self.assertIn("teacher-team-copy", teacher_ids)

    def test_document_theory_named_routes_are_registered(self):
        paths = {route.path for route in app.routes}
        self.assertIn("/api/mms/models", paths)
        self.assertIn("/api/mms/models/{model_name}", paths)
        self.assertIn("/api/mms/branches", paths)
        self.assertIn("/api/mdk/adapters", paths)
        self.assertIn("/api/mdk/parse", paths)
        self.assertIn("/api/mdk/import-jobs", paths)
        self.assertIn("/api/mdk/import-jobs/{job_id}", paths)
        self.assertIn("/api/mdk/import-jobs/{job_id}/apply", paths)
        self.assertIn("/api/projects/{project_id}/branches/{branch}/views", paths)
        self.assertIn("/api/projects/{project_id}/branches/{branch}/views/{view_id}", paths)
        self.assertIn("/api/projects/{project_id}/branches/{branch}/views/{view_id}/diagram", paths)
        self.assertIn("/api/docgen/pdf", paths)

    def test_view_routes_resolve_scoped_elements_and_diagram(self):
        created = self.client.post(
            "/api/projects/satellite-power/branches/main/elements",
            json={
                "id": "VIEW-API-001",
                "name": "API View",
                "type": "View",
                "attributes": {
                    "included_elements": ["REQ-001", "BLK-POWER"],
                    "query": {"types": ["TestCase"], "text": "供电", "relation_depth": 0},
                },
                "relations": [],
            },
            headers={"X-User": "engineer", "X-Role": "user"},
        )
        self.assertEqual(created.status_code, 200)

        views = self.client.get("/api/projects/satellite-power/branches/main/views")
        self.assertEqual(views.status_code, 200)
        self.assertTrue(any(view["id"] == "VIEW-API-001" for view in views.json()["views"]))

        payload = self.client.get("/api/projects/satellite-power/branches/main/views/VIEW-API-001")
        self.assertEqual(payload.status_code, 200)
        self.assertIn("REQ-001", payload.json()["element_ids"])
        self.assertIn("BLK-POWER", payload.json()["element_ids"])

        diagram = self.client.get("/api/projects/satellite-power/branches/main/views/VIEW-API-001/diagram")
        self.assertEqual(diagram.status_code, 200)
        self.assertTrue(any(node["id"] == "VIEW-API-001" for node in diagram.json()["diagram"]["nodes"]))

    def test_mdk_adapters_route_exposes_capabilities(self):
        response = self.client.get("/api/mdk/adapters")
        self.assertEqual(response.status_code, 200)
        adapters = {adapter["id"]: adapter for adapter in response.json()["adapters"]}
        self.assertIn("cameo", adapters)
        self.assertFalse(adapters["cameo"]["can_write"])
        self.assertIn("xmi", adapters["cameo"]["formats"])
        self.assertEqual(adapters["cameo"]["vendor"], "Dassault Systemes")
        self.assertIn(".xmi", adapters["cameo"]["supported_extensions"])

    def test_mdk_parse_returns_mapping_report(self):
        response = self.client.post(
            "/api/mdk/parse",
            json={
                "filename": "model.json",
                "tool": "json",
                "content": {
                    "elements": [
                        {"id": "REQ-API-REPORT", "name": "API import report", "type": "Requirement"}
                    ]
                },
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["parsed_model"]["adapter"], "json")
        self.assertEqual(payload["mapping_report"]["imported"], 1)

    def test_mdk_push_accepts_adapter_parsed_xmi_payload(self):
        response = self.client.post(
            "/api/mdk/push",
            json={
                "project": "satellite-power",
                "branch": "main",
                "model": {
                    "format": "xmi",
                    "elements": [
                        {"id": "BLK-XMI-PUSH", "name": "Adapter parsed XMI", "type": "Block", "relations": []}
                    ],
                    "mapping_report": {"adapter": "cameo", "imported": 1},
                },
            },
            headers={"X-User": "engineer", "X-Role": "user"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["imported"], 1)
        self.assertEqual(payload["mapping_report"]["adapter"], "cameo")

    def test_mdk_import_job_preview_and_apply(self):
        created = self.client.post(
            "/api/mdk/import-jobs",
            json={
                "project": "satellite-power",
                "branch": "main",
                "filename": "model.json",
                "tool": "json",
                "content": {
                    "elements": [
                        {"id": "REQ-JOB-001", "name": "Job import", "type": "Requirement"}
                    ]
                },
            },
            headers={"X-User": "engineer", "X-Role": "user"},
        )
        self.assertEqual(created.status_code, 200)
        job = created.json()["job"]
        self.assertEqual(job["status"], "parsed")
        self.assertEqual(job["mapping_report"]["imported"], 1)

        fetched = self.client.get(f"/api/mdk/import-jobs/{job['id']}")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["job"]["id"], job["id"])

        applied = self.client.post(
            f"/api/mdk/import-jobs/{job['id']}/apply",
            json={"commit": True, "message": "Apply import job"},
            headers={"X-User": "engineer", "X-Role": "user"},
        )
        self.assertEqual(applied.status_code, 200)
        payload = applied.json()
        self.assertEqual(payload["job"]["status"], "applied")
        self.assertEqual(payload["result"]["imported"], 1)
        self.assertIn("commit", payload["result"])

    def test_mdk_import_job_applies_json_elements_with_forward_relations(self):
        created = self.client.post(
            "/api/mdk/import-jobs",
            json={
                "project": "satellite-power",
                "branch": "main",
                "filename": "upload-graph.json",
                "tool": "json",
                "content": {
                    "elements": [
                        {
                            "id": "REQ-FWD-001",
                            "name": "Forward relation requirement",
                            "type": "Requirement",
                            "relations": [{"type": "satisfy", "target": "BLK-FWD-001"}],
                        },
                        {
                            "id": "BLK-FWD-001",
                            "name": "Forward relation block",
                            "type": "Block",
                            "relations": [],
                        },
                    ]
                },
            },
            headers={"X-User": "engineer", "X-Role": "user"},
        )
        self.assertEqual(created.status_code, 200)
        job_id = created.json()["job"]["id"]

        applied = self.client.post(
            f"/api/mdk/import-jobs/{job_id}/apply",
            json={"commit": False},
            headers={"X-User": "engineer", "X-Role": "user"},
        )
        self.assertEqual(applied.status_code, 200)
        self.assertEqual(applied.json()["result"]["imported"], 2)

        element = self.client.get("/api/projects/satellite-power/branches/main/elements/REQ-FWD-001")
        self.assertEqual(element.status_code, 200)
        self.assertEqual(element.json()["element"]["relations"][0]["target"], "BLK-FWD-001")

    def test_frontend_dir_resolution_requires_built_dist_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            frontend_dist = root / "frontend" / "dist"
            static_dir = root / "static"
            frontend_dist.mkdir(parents=True)
            static_dir.mkdir(parents=True)
            (frontend_dist / "index.html").write_text("dist", encoding="utf-8")
            (static_dir / "index.html").write_text("static", encoding="utf-8")

            frontend_dir, mode = determine_frontend_dir(frontend_dist, static_dir, allow_static_frontend=False)

            self.assertEqual(frontend_dir, frontend_dist)
            self.assertEqual(mode, "dist")

    def test_frontend_dir_resolution_does_not_silently_fallback_to_static(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            frontend_dist = root / "frontend" / "dist"
            static_dir = root / "static"
            static_dir.mkdir(parents=True)
            (static_dir / "index.html").write_text("static", encoding="utf-8")

            frontend_dir, mode = determine_frontend_dir(frontend_dist, static_dir, allow_static_frontend=False)

            self.assertIsNone(frontend_dir)
            self.assertEqual(mode, "missing")

    def test_frontend_dir_resolution_can_explicitly_enable_static_fallback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            frontend_dist = root / "frontend" / "dist"
            static_dir = root / "static"
            static_dir.mkdir(parents=True)
            (static_dir / "index.html").write_text("static", encoding="utf-8")

            frontend_dir, mode = determine_frontend_dir(frontend_dist, static_dir, allow_static_frontend=True)

            self.assertEqual(frontend_dir, static_dir)
            self.assertEqual(mode, "static-fallback")


if __name__ == "__main__":
    unittest.main()
