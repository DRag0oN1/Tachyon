"""Real local HTTP/storage revision contracts on original non-VEX geometry.

These declared computational attachments do not qualify mechanical operation,
collision clearance, powered scoring, AI intent handling or a complete robot.
"""
from copy import deepcopy
import logging

from fastapi.testclient import TestClient
import pytest

from fixture_support import load_json, save_json
from tachyon.app import create_app
from tachyon.cad.prepare import prepare_component


@pytest.fixture
def draft_case(prepared_workspace, caplog):
    caplog.set_level(logging.ERROR, logger="uvicorn.error")
    w = prepared_workspace
    manifest = load_json(w.manifest_path)
    port = deepcopy(manifest["components"][0]["ports"][0])
    port["id"] = "alternate_face_reference"
    port["positionM"][2] += .0127
    port["evidence"] = "Original calibration base-face reference, 12.7 mm along its face; computational attachment only"
    manifest["components"][0]["ports"].append(port)
    save_json(w.manifest_path, manifest)
    prepare_component(w.catalog(), w.component)
    app = create_app(w.settings)
    with TestClient(app, base_url=w.settings.ui_origin, client=("127.0.0.1", 50000)) as client:
        client.headers["X-Tachyon-Session"] = app.state.session
        yield client, w


def body(w):
    return {"designId": "original-fixture", "rootInstanceId": "base", "configurationId": "first",
        "subsystems": [{"id": "support", "name": "Original fixture support"}, {"id": "carrier", "name": "Original fixture carrier"}],
        "instances": [{"id": "base", "componentId": w.component.id, "subsystemId": "support"},
            {"id": "carrier", "componentId": w.component.id, "subsystemId": "carrier", "parentId": "base"},
            {"id": "dependent", "componentId": w.component.id, "subsystemId": "carrier", "parentId": "carrier"}],
        "relationships": [{"id": "carrier-mount", "parentInstanceId": "base", "parentPortId": "calibration_reference", "childInstanceId": "carrier", "childPortId": "calibration_reference"},
            {"id": "tool-mount", "parentInstanceId": "carrier", "parentPortId": "calibration_reference", "childInstanceId": "dependent", "childPortId": "calibration_reference"}],
        "actions": [{"actionId": "inspect-carrier", "subsystemId": "carrier", "instanceIds": ["carrier", "dependent"],
                     "anchors": [{"id": "carrier-face", "instanceId": "carrier", "portId": "calibration_reference"}]}]}


def create(client, w):
    response = client.post("/api/assembly-drafts", json=body(w))
    assert response.status_code == 200, response.text
    assert response.headers["Cache-Control"] == "private, no-store"
    result = response.json()
    assert result["kind"] == "manual_assembly_draft" and result["aiGenerated"] is False
    assert result["readiness"]["completeRobot"] is False
    return result


def preview(client, initial):
    response = client.post("/api/assembly-drafts/original-fixture/preview", json={
        "baseRevisionId": initial["accepted"]["id"], "relationshipId": "carrier-mount",
        "parentPortId": "alternate_face_reference", "configurationId": "alternate"})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["accepted"] == initial["accepted"]
    assert result["bindings"] == initial["bindings"]
    for member in ("carrier", "dependent"):
        assert result["candidateWorldTransforms"][member][14] == pytest.approx(initial["worldTransforms"][member][14] + .0127)
    assert result["candidateBindings"]["revisionId"] == result["candidate"]["id"]
    return result


def test_real_http_preview_apply_and_undo_preserve_exact_links_and_descendant_transforms(draft_case):
    client, w = draft_case
    initial = create(client, w)
    candidate = preview(client, initial)
    decision = {"action": "apply", "baseRevisionId": initial["accepted"]["id"], "candidateRevisionId": candidate["candidate"]["id"]}
    applied = client.post("/api/assembly-drafts/original-fixture/decision", json=decision)
    assert applied.status_code == 200, applied.text
    current = applied.json()
    assert current["accepted"] == candidate["candidate"]
    assert current["bindings"] == candidate["candidateBindings"]
    assert client.post("/api/assembly-drafts/original-fixture/decision", json=decision).json() == current
    undone = client.post("/api/assembly-drafts/original-fixture/decision", json={"action": "undo", "baseRevisionId": current["accepted"]["id"]})
    assert undone.status_code == 200
    assert undone.json()["accepted"] == initial["accepted"]
    assert undone.json()["bindings"] == initial["bindings"]
    assert undone.json()["worldTransforms"] == initial["worldTransforms"]


def test_discard_and_conflicts_leave_accepted_data_untouched(draft_case):
    client, w = draft_case
    initial = create(client, w)
    candidate = preview(client, initial)
    bad = client.post("/api/assembly-drafts/original-fixture/decision", json={"action": "apply", "baseRevisionId": "stale", "candidateRevisionId": candidate["candidate"]["id"]})
    assert bad.status_code == 409
    discarded = client.post("/api/assembly-drafts/original-fixture/decision", json={"action": "discard", "baseRevisionId": initial["accepted"]["id"], "candidateRevisionId": candidate["candidate"]["id"]})
    assert discarded.status_code == 200
    assert discarded.json()["candidate"] is None
    assert discarded.json()["accepted"] == initial["accepted"]
    assert client.post("/api/assembly-drafts", json=body(w)).status_code == 409


def test_current_catalog_and_rights_are_rechecked_before_mutation(draft_case):
    client, w = draft_case
    initial = create(client, w)
    rights = load_json(w.rights_path)
    rights["records"][0]["operations"]["assembly_placement"]["status"] = "unverified"
    save_json(w.rights_path, rights)
    response = client.post("/api/assembly-drafts/original-fixture/preview", json={"baseRevisionId": initial["accepted"]["id"], "relationshipId": "carrier-mount", "parentPortId": "alternate_face_reference", "configurationId": "alternate"})
    assert response.status_code == 422
    assert response.json()["code"] == "SOURCE_NOT_QUALIFIED"


def test_reference_only_assets_and_client_supplied_permissions_cannot_enter_designs(draft_case):
    client, w = draft_case
    fake = body(w)
    fake["qualifiedOperations"] = ["assembly_placement"]
    assert client.post("/api/assembly-drafts", json=fake).status_code == 422
    manifest = load_json(w.manifest_path)
    manifest["components"][0]["referenceOnly"] = True
    save_json(w.manifest_path, manifest)
    prepare_component(w.catalog(), w.component)
    response = client.post("/api/assembly-drafts", json=body(w))
    assert response.status_code == 422 and response.json()["code"] == "REFERENCE_ONLY_COMPONENT"
