"""Actual FastAPI requests against private, original non-VEX calibration data.

Checklist command: python -m pytest server/tests/test_catalog.py server/tests/test_asset_api.py
No network/provider calls or manufacturer CAD are used by these tests.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import date, timedelta
import logging

from fastapi.testclient import TestClient
import pytest

from fixture_support import FIXTURE_ID, FixtureWorkspace, digest, load_json, save_json
from glb_support import read_glb
from tachyon.app import create_app
from tachyon.config import Settings


@pytest.fixture(autouse=True)
def private_test_environment(monkeypatch, caplog):
    # Do not inspect real credentials or print even these ephemeral owner tokens.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("TACHYON_AI_MODEL", raising=False)
    caplog.set_level(logging.ERROR, logger="uvicorn.error")


@contextmanager
def owner_client(workspace, host="127.0.0.1"):
    app = create_app(workspace.settings)
    with TestClient(app, base_url=workspace.settings.ui_origin, client=(host, 51000)) as client:
        client.headers["X-Tachyon-Session"] = app.state.session
        yield client


@pytest.fixture
def api(prepared_workspace):
    with owner_client(prepared_workspace) as client:
        yield client


def assert_private(response):
    assert response.headers["Cache-Control"] == "private, no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def asset_url(workspace):
    return workspace.catalog().prepared(workspace.component)["meshUrl"]


def test_health_requires_no_token_and_does_not_claim_provider_or_robot_readiness(api):
    response = api.get("/api/health", headers={"X-Tachyon-Session": ""})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["providerConfigured"] is False
    assert response.json()["cadProfile"] == "user_provided_local"
    assert_private(response)


@pytest.mark.parametrize("path", ["/api/catalog", "/api/sources", "/api/capabilities", "/api/workspace",
                                    f"/api/inspection/{FIXTURE_ID}", "/api/assets/" + "0" * 64 + ".glb"])
@pytest.mark.parametrize("token", ["", "invalid-owner-token"])
def test_private_routes_require_current_owner_token(api, path, token):
    response = api.get(path, headers={"X-Tachyon-Session": token})
    assert response.status_code == 401
    assert response.json()["code"] == "SESSION_REQUIRED"
    assert_private(response)


def test_non_ascii_session_header_is_private_unauthorized_response(api):
    response = api.get("/api/catalog", headers=[(b"X-Tachyon-Session", b"\xff")])
    assert response.status_code == 401
    assert response.json()["code"] == "SESSION_REQUIRED"
    assert_private(response)


def test_patch_and_query_or_cookie_token_cannot_bypass_authentication(api):
    before = api.get("/api/workspace").json()
    token = api.headers["X-Tachyon-Session"]
    api.cookies.set("session", token)
    response = api.patch("/api/workspace", params={"session": token},
                         headers={"X-Tachyon-Session": ""}, json={"preferences": {"theme": "shift"}})
    assert response.status_code == 401
    assert_private(response)
    assert api.get("/api/workspace").json() == before


@pytest.mark.parametrize("origin", ["https://example.invalid", "null", "http://localhost:8000",
                                      "http://127.0.0.1:8001", "http://127.0.0.1:8000.example.invalid"])
def test_correct_token_does_not_authorize_another_origin(api, origin):
    response = api.get("/api/catalog", headers={"Origin": origin})
    assert response.status_code == 403
    assert response.json()["code"] == "ORIGIN_REJECTED"
    assert_private(response)
    assert "Access-Control-Allow-Origin" not in response.headers


@pytest.mark.parametrize("origin", [None, "http://127.0.0.1:8000", "http://127.0.0.1:8000/"])
def test_owner_origin_and_same_origin_requests_are_allowed(api, origin):
    response = api.get("/api/catalog", headers={"Origin": origin} if origin else {})
    assert response.status_code == 200
    assert len(response.json()["components"]) == 1
    assert_private(response)


def test_catalog_and_binary_asset_match_prepared_identity(api, prepared_workspace, tmp_path):
    workspace = prepared_workspace
    source_before = workspace.source_path.read_bytes()
    response = api.get("/api/catalog")
    assert_private(response)
    state = response.json()
    assert state["blockers"] == []
    record = state["components"][0]
    assert record["id"] == FIXTURE_ID
    assert record["geometryClass"] == "test_fixture"
    assert record["originKind"] == "tachyon_authored"
    assert "non-VEX" in record["name"] and "test_fixture" in record["name"]
    assert record["completeRobot"] is False
    assert record["sourceSha256"] == digest(workspace.source_path)
    response = api.get(record["meshUrl"])
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "model/gltf-binary"
    assert_private(response)
    served = tmp_path / "served.glb"
    served.write_bytes(response.content)
    assert digest(served) == record["meshSha256"]
    assert read_glb(served)["triangleCount"] == 24
    assert workspace.source_path.read_bytes() == source_before
    # Public provenance identifies sources without leaking local filesystem paths/evidence.
    assert "sourcePath" not in record and "evidencePath" not in record
    assert str(workspace.settings.root) not in str(state)
    assert workspace.evidence_path.read_text() not in str(state)


def test_source_inspection_preserves_native_parents_without_inventing_mates(api):
    component = api.get("/api/catalog").json()["components"][0]
    response = api.get(f"/api/inspection/{FIXTURE_ID}")
    assert response.status_code == 200
    assert_private(response)
    inspection = response.json()
    assert inspection["kind"] == "imported_source"
    assert inspection["componentId"] == FIXTURE_ID
    assert inspection["sourceSha256"] == component["sourceSha256"]
    assert inspection["meshSha256"] == component["meshSha256"]
    assert inspection["nodes"] == component["nativeHierarchy"]
    assert inspection["ports"] == component["ports"]
    assert inspection["completeRobot"] is False and inspection["joints"] == []
    nodes = {node["name"]: node for node in inspection["nodes"]}
    assert nodes["calibration_offset_block"]["parentId"] == nodes["calibration_offset_group"]["id"]
    expected_edges = {(node["parentId"], node["id"]) for node in inspection["nodes"] if node["parentId"] is not None}
    assert {(edge["parentId"], edge["childId"]) for edge in inspection["relationships"]} == expected_edges
    assert all(edge["kind"] == "native_parent" and "not a verified mechanical mate" in edge["evidence"]
               for edge in inspection["relationships"])
    assert inspection["limitations"]


@pytest.mark.parametrize("provider_configured", [False, True])
def test_provider_configuration_does_not_enable_unimplemented_capabilities(api, monkeypatch, provider_configured):
    if provider_configured:
        monkeypatch.setenv("OPENAI_API_KEY", "test-fixture-placeholder-not-a-credential")
        monkeypatch.setenv("TACHYON_AI_MODEL", "test-fixture-model")
    assert api.get("/api/health").json()["providerConfigured"] is provider_configured
    response = api.get("/api/capabilities")
    assert_private(response)
    state = response.json()
    assert state["canInspect"] is True
    assert state["canGenerateStrategy"] is False
    assert state["canGenerateRobot"] is False
    assert state["canEdit"] is False
    assert state["reasons"]


def test_empty_workspace_has_actionable_unavailability_and_no_assets(tmp_path):
    settings = Settings(tmp_path, tmp_path / "data")
    app = create_app(settings)
    with TestClient(app, client=("127.0.0.1", 51000)) as client:
        client.headers["X-Tachyon-Session"] = app.state.session
        response = client.get("/api/catalog")
        assert response.json()["components"] == []
        assert response.json()["blockers"][0]["code"] == "NO_LOCAL_CAD"
        assert_private(response)
        assert client.get("/api/capabilities").json()["canInspect"] is False
        assert client.get(f"/api/inspection/{FIXTURE_ID}").status_code == 404


def test_registration_without_conversion_cannot_enable_inspection(calibration_workspace):
    calibration_workspace.catalog().register()
    with owner_client(calibration_workspace) as client:
        state = client.get("/api/catalog").json()
        assert state["components"] == []
        assert state["blockers"][0]["code"] == "MESH_NOT_PREPARED"
        assert client.get("/api/capabilities").json()["canInspect"] is False


@pytest.mark.parametrize("mesh_hash", ["invalid", "A" * 64, "0" * 63, "0" * 65, "0" * 64])
def test_invalid_and_unknown_content_hashes_do_not_serve_geometry(api, mesh_hash):
    response = api.get(f"/api/assets/{mesh_hash}.glb")
    assert response.status_code == 404
    assert response.json()["code"] == "ASSET_NOT_FOUND"
    assert_private(response)


@pytest.mark.parametrize("change,code", [
    ("revoked_acquisition", "SOURCE_NOT_QUALIFIED"),
    ("missing_loopback", "SOURCE_NOT_QUALIFIED"),
    ("expired_evidence", "RIGHTS_EVIDENCE_EXPIRED"),
    ("changed_evidence", "RIGHTS_EVIDENCE_CHANGED"),
    ("wrong_evidence_hash", "RIGHTS_EVIDENCE_CHANGED"),
    ("wrong_source_identity", "SOURCE_NOT_QUALIFIED"),
    ("changed_source", "SOURCE_HASH_MISMATCH"),
])
def test_every_request_rechecks_current_rights_source_and_evidence(api, prepared_workspace, change, code):
    workspace = prepared_workspace
    url = asset_url(workspace)
    assert api.get(url).status_code == 200
    if change == "revoked_acquisition":
        workspace.update_permission("acquisition_storage", status="disallowed")
    elif change == "missing_loopback":
        rights = load_json(workspace.rights_path)
        del rights["records"][0]["operations"]["loopback_display"]
        save_json(workspace.rights_path, rights)
    elif change == "expired_evidence":
        workspace.update_permission("loopback_display", expiresOn=(date.today() - timedelta(days=1)).isoformat())
    elif change == "changed_evidence":
        workspace.evidence_path.write_text("Changed evidence after native preparation.\n")
    elif change == "wrong_evidence_hash":
        workspace.update_permission("loopback_display", evidenceSha256="0" * 64)
    elif change == "wrong_source_identity":
        rights = load_json(workspace.rights_path)
        rights["records"][0]["sourceSha256"] = "0" * 64
        save_json(workspace.rights_path, rights)
    else:
        workspace.source_path.write_bytes(workspace.source_path.read_bytes() + b"\nsource tamper\n")
    response = api.get(url)
    assert response.status_code == 422
    assert response.json()["code"] == code
    assert_private(response)
    state = api.get("/api/catalog").json()
    assert state["components"] == [] and state["blockers"][0]["code"] == code
    assert api.get("/api/capabilities").json()["canInspect"] is False
    assert api.get(f"/api/inspection/{FIXTURE_ID}").status_code == 404


def test_tampered_mesh_is_never_returned_by_api(api, prepared_workspace):
    workspace = prepared_workspace
    record = workspace.catalog().prepared(workspace.component)
    mesh = workspace.data_dir / "meshes" / (record["meshSha256"] + ".glb")
    mesh.write_bytes(b"tampered binary geometry")
    response = api.get(record["meshUrl"])
    assert response.status_code == 422
    assert response.json()["code"] == "MESH_HASH_MISMATCH"
    assert_private(response)
    assert api.get("/api/catalog").json()["components"] == []


def test_forged_receipt_cannot_certify_fixture_as_imported(api, prepared_workspace):
    workspace = prepared_workspace
    receipt = workspace.catalog().receipt_path(workspace.component)
    record = load_json(receipt)
    record["geometryClass"] = "verified_imported_component"
    save_json(receipt, record)
    response = api.get("/api/catalog")
    assert response.json()["components"] == []
    assert response.json()["blockers"][0]["code"] == "STALE_MESH"
    assert api.get(record["meshUrl"]).status_code == 422


@pytest.mark.parametrize("host", ["192.168.1.25", "testclient", "203.0.113.15"])
def test_nonloopback_clients_cannot_inherit_loopback_permission(prepared_workspace, host):
    workspace = prepared_workspace
    url = asset_url(workspace)
    with owner_client(workspace, host=host) as client:
        response = client.get("/api/catalog", headers={"X-Forwarded-For": "127.0.0.1"})
        assert response.json()["components"] == []
        assert response.json()["blockers"][0]["code"] == "SOURCE_NOT_QUALIFIED"
        assert_private(response)
        assert client.get("/api/capabilities").json()["canInspect"] is False
        response = client.get(url)
        assert response.status_code == 422 and response.json()["code"] == "SOURCE_NOT_QUALIFIED"
        assert_private(response)


def test_ipv6_loopback_is_local_display(prepared_workspace):
    with owner_client(prepared_workspace, host="::1") as client:
        assert len(client.get("/api/catalog").json()["components"]) == 1


def test_explicit_fixture_only_lan_evidence_is_separate_and_revocable(prepared_workspace):
    workspace = prepared_workspace
    url = asset_url(workspace)
    rights = load_json(workspace.rights_path)
    evidence = workspace.data_dir / "evidence/lan-test-authorship.txt"
    evidence.write_text("Tachyon self-authored calibration test_fixture only.\n"
                        f"Source SHA-256: {workspace.component.source_sha256}\n"
                        "Explicit LAN display permission for this temporary pytest fixture only.\n"
                        "This grants nothing for manufacturer, research, or user CAD.\n")
    permission = deepcopy(rights["records"][0]["operations"]["loopback_display"])
    permission.update(evidencePath="evidence/lan-test-authorship.txt", evidenceSha256=digest(evidence))
    rights["records"][0]["operations"]["lan_display"] = permission
    del rights["records"][0]["operations"]["loopback_display"]
    save_json(workspace.rights_path, rights)
    with owner_client(workspace, host="192.168.1.25") as client:
        components = client.get("/api/catalog").json()["components"]
        assert len(components) == 1
        assert components[0]["qualifiedOperations"] == ["acquisition_storage", "lan_display"]
        response = client.get(url)
        assert response.status_code == 200
        assert_private(response)
        evidence.write_text("Changed LAN evidence\n")
        response = client.get(url)
        assert response.status_code == 422 and response.json()["code"] == "RIGHTS_EVIDENCE_CHANGED"


@pytest.mark.parametrize("ui_origin,backend_url", [
    ("http://192.168.1.10:5173", "http://127.0.0.1:8000"),
    ("http://tachyon-phone.local:5173", "http://127.0.0.1:8000"),
    ("http://127.0.0.1:8000", "http://192.168.1.10:8000"),
    ("http://127.0.0.1:8000", "http://tachyon-phone.local:8000"),
])
def test_loopback_proxy_requires_separate_lan_rights_for_declared_origin_or_host(
        prepared_workspace, ui_origin, backend_url):
    workspace = FixtureWorkspace(Settings(
        root=prepared_workspace.settings.root, data_dir=prepared_workspace.data_dir,
        ui_origin=ui_origin))
    record = workspace.catalog().prepared(workspace.component)
    app = create_app(workspace.settings)
    # Model the development proxy: the backend peer and sometimes its Host are
    # loopback, while the declared UI origin or requested Host identifies LAN use.
    with TestClient(app, base_url=backend_url, client=("127.0.0.1", 51000)) as client:
        client.headers.update({"X-Tachyon-Session": app.state.session, "Origin": ui_origin})
        response = client.get("/api/catalog")
        assert response.status_code == 200
        assert response.json()["components"] == []
        assert response.json()["blockers"][0]["code"] == "SOURCE_NOT_QUALIFIED"
        assert_private(response)
        assert client.get("/api/capabilities").json()["canInspect"] is False
        response = client.get(record["meshUrl"])
        assert response.status_code == 422
        assert response.json()["code"] == "SOURCE_NOT_QUALIFIED"
        assert_private(response)
        assert client.get(f"/api/inspection/{FIXTURE_ID}").status_code == 404

        # This new evidence grants LAN display solely for the temporary original
        # fixture. Removing loopback permission proves the scopes are independent.
        rights = load_json(workspace.rights_path)
        evidence = workspace.data_dir / "evidence/proxy-lan-test-authorship.txt"
        evidence.write_text(
            "Tachyon self-authored calibration test_fixture only; non-VEX.\n"
            f"Source SHA-256: {workspace.component.source_sha256}\n"
            "Explicit lan_display permission for this temporary proxy regression test.\n"
            "No permission for manufacturer, research, user, or other source CAD.\n")
        permission = deepcopy(rights["records"][0]["operations"].pop("loopback_display"))
        permission.update(evidencePath="evidence/proxy-lan-test-authorship.txt",
                          evidenceSha256=digest(evidence))
        rights["records"][0]["operations"]["lan_display"] = permission
        save_json(workspace.rights_path, rights)

        response = client.get("/api/catalog")
        assert response.status_code == 200
        assert_private(response)
        component = response.json()["components"][0]
        assert component["id"] == FIXTURE_ID and component["geometryClass"] == "test_fixture"
        assert component["qualifiedOperations"] == ["acquisition_storage", "lan_display"]
        assert component["sourceSha256"] == record["sourceSha256"]
        assert component["meshSha256"] == record["meshSha256"]
        assert client.get("/api/capabilities").json()["canInspect"] is True
        response = client.get(record["meshUrl"])
        assert response.status_code == 200
        assert response.content == (workspace.data_dir / "meshes" / (record["meshSha256"] + ".glb")).read_bytes()
        assert_private(response)
        assert client.get(f"/api/inspection/{FIXTURE_ID}").status_code == 200


def test_workspace_preferences_and_selection_persist_with_rotated_owner_session(prepared_workspace):
    workspace = prepared_workspace
    with owner_client(workspace) as client:
        assert client.get("/api/workspace").json() == {
            "preferences": {"theme": "snap", "mode": "simple"}, "activeComponentId": None}
        response = client.patch("/api/workspace", json={
            "preferences": {"theme": "shift", "mode": "advanced"}, "activeComponentId": FIXTURE_ID})
        assert response.status_code == 200
        assert_private(response)
        saved = response.json()
        previous_session = client.headers["X-Tachyon-Session"]
    with owner_client(workspace) as restarted:
        assert restarted.headers["X-Tachyon-Session"] != previous_session
        assert restarted.get("/api/workspace").json() == saved
        response = restarted.get("/api/workspace", headers={"X-Tachyon-Session": previous_session})
        assert response.status_code == 401
        assert_private(response)
        response = restarted.patch("/api/workspace", json={"activeComponentId": None})
        assert response.json()["activeComponentId"] is None
        assert response.json()["preferences"] == saved["preferences"]


def test_partial_theme_patch_preserves_advanced_mode_and_null_is_ignored(api):
    api.patch("/api/workspace", json={"preferences": {"theme": "shift", "mode": "advanced"}})
    response = api.patch("/api/workspace", json={"preferences": {"theme": "snap"}})
    assert response.status_code == 200
    assert response.json()["preferences"] == {"theme": "snap", "mode": "advanced"}
    response = api.patch("/api/workspace", json={"preferences": {"theme": None, "mode": None}})
    assert response.json()["preferences"] == {"theme": "snap", "mode": "advanced"}
    response = api.patch("/api/workspace", json={"preferences": None})
    assert response.json()["preferences"] == {"theme": "snap", "mode": "advanced"}


@pytest.mark.parametrize("patch", [
    {"preferences": {"theme": "invalid"}}, {"preferences": {"mode": "expert"}},
    {"preferences": {"unrecognized": True}}, {"unrecognized": True},
    {"activeComponentId": "missing-component"},
])
def test_invalid_workspace_patches_do_not_change_saved_state(api, patch):
    before = api.get("/api/workspace").json()
    response = api.patch("/api/workspace", json=patch)
    assert response.status_code == 422
    assert_private(response)
    assert api.get("/api/workspace").json() == before


@pytest.mark.parametrize("path", ["/api/source/calibration.step", "/sources/calibration.step",
                                   "/catalog/rights.json", "/evidence/calibration-authorship.txt",
                                   "/api/assets/export", "/api/share", "/docs", "/openapi.json"])
def test_no_source_evidence_export_or_public_documentation_routes(api, path):
    assert api.get(path).status_code == 404


def test_existing_display_cache_does_not_infer_conversion_or_assembly_rights(api, prepared_workspace):
    workspace = prepared_workspace
    url = asset_url(workspace)
    workspace.update_permission("conversion", status="disallowed")
    workspace.update_permission("assembly_placement", status="disallowed")
    response = api.get(url)
    assert response.status_code == 200
    assert_private(response)
    component = api.get("/api/catalog").json()["components"][0]
    assert component["qualifiedOperations"] == ["acquisition_storage", "loopback_display"]
    assert component["completeRobot"] is False
    assert api.get("/api/capabilities").json()["canGenerateRobot"] is False


@pytest.mark.parametrize("contents", ["null", "[]", "42", '{"meshSha256":null}'])
def test_malformed_receipt_blocks_only_its_component_and_never_causes_api_500(api, prepared_workspace, contents):
    workspace = prepared_workspace
    url = asset_url(workspace)
    workspace.catalog().receipt_path(workspace.component).write_text(contents)
    response = api.get("/api/catalog")
    assert response.status_code == 200
    assert_private(response)
    assert response.json()["components"] == []
    assert response.json()["blockers"][0]["code"] == "INVALID_RECEIPT"
    response = api.get(url)
    assert response.status_code == 404
    assert response.json()["code"] == "ASSET_NOT_FOUND"
    assert_private(response)


def test_unsupported_manifest_class_is_an_explicit_private_api_error(api, prepared_workspace):
    prepared_workspace.update_component(geometryClass="unsupported_geometry_class")
    response = api.get("/api/catalog")
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_MANIFEST"
    assert_private(response)


def test_unexpected_failure_returns_private_sanitized_error_without_mutating_workspace(api, monkeypatch, caplog):
    from tachyon.cad.catalog import Catalog

    before = api.get("/api/workspace").json()
    sensitive_detail = "fake-private-file-and-token-fixture-for-redaction-test"

    def failure(*args, **kwargs):
        raise RuntimeError(sensitive_detail)

    monkeypatch.setattr(Catalog, "public", failure)
    response = api.get("/api/catalog")
    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    assert response.json()["retryable"] is True
    assert sensitive_detail not in response.text and sensitive_detail not in caplog.text
    assert_private(response)
    assert api.get("/api/workspace").json() == before
