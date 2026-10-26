"""Owner-only discovery metadata; no CAD or mechanical acceptance is claimed.

The private recipes and stored records here are explicitly synthetic schema
fixtures. Public proposal identities are checked against the existing handoff.
"""
from copy import deepcopy
import importlib
import json
import logging
from pathlib import Path
import shutil

from fastapi.testclient import TestClient
import pytest

from tachyon import assemblies as A, realization as R, strategy_runtime as SR
from tachyon.app import create_app
from tachyon.config import Settings
from tachyon.design_api import router


PUBLIC_ROOT = Path(__file__).resolve().parents[2]
ARCHITECTURES = {
    "A": "strategy-spec-4c5452f1550499ebcd54cab6:architecture-a:f5bff3b56bf1b3549372d7ae",
    "B": "strategy-spec-4c5452f1550499ebcd54cab6:architecture-b:213d5164d5b6ff3a239e0bdd",
}


@pytest.fixture
def catalog_case(tmp_path, caplog):
    caplog.set_level(logging.ERROR, logger="uvicorn.error")
    for name in ("manifest.json", "design/manifest.json", "design/architecture-proposals.json", "strategy-spec-v2.json"):
        relative = SR.HANDOFF / name
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PUBLIC_ROOT / relative, target)
    settings = Settings(root=tmp_path, data_dir=tmp_path / "private")
    app = create_app(settings)
    with TestClient(app, base_url=settings.ui_origin, client=("127.0.0.1", 50000)) as client:
        client.headers["X-Tachyon-Session"] = app.state.session
        yield client, app, settings


def forbid_cad_and_inference(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("The design index must not load CAD, qualify rights, or run inference")
    monkeypatch.setattr(R, "Catalog", forbidden)
    monkeypatch.setattr(importlib.import_module("tachyon.app"), "Catalog", forbidden)
    for name in ("qualified_catalog", "build_pose", "qualify_robot"):
        monkeypatch.setattr(R, name, forbidden)
    for name in ("load_artifacts", "generate", "_execute"):
        monkeypatch.setattr(SR, name, forbidden)
    monkeypatch.setattr(R.RealizationService, "_load", forbidden)


def synthetic_recipe(alternative="A"):
    return {
        "id": "metadata-only-fixture-" + alternative, "alternative": alternative,
        "roleComponentIds": {"chassis": ["original-ui-part"], "scorer": ["original-ui-part"]},
        "portFrames": {},
        "template": {
            "rootInstanceId": "base",
            "instances": [{"id": "base", "componentId": "original-ui-part", "subsystemId": "chassis"},
                          {"id": "tool", "componentId": "original-ui-part", "subsystemId": "scorer", "parentId": "base"}],
            "subsystems": [{"id": "chassis", "name": "Synthetic chassis metadata"},
                           {"id": "scorer", "name": "Synthetic scorer metadata"}],
            "relationships": [{"id": "mount", "parentInstanceId": "base", "parentPortId": "fixture-port",
                               "childInstanceId": "tool", "childPortId": "fixture-port"}],
        },
        "configurations": {"lower": {"jointPositions": {}}},
    }


def write_recipes(settings, recipes):
    path = settings.data_dir / "catalog/assembly-recipes.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schemaVersion": 1, "recipes": recipes}))
    return path


def store_records(app, settings, records):
    service = R.RealizationService(settings, app.state.store)
    with service._database(write=True) as db:
        for data in records:
            service._save(db, data)
    return service


def cached_record(index=0):
    # Deliberately untrusted cached geometry/readiness/history; index may expose
    # navigation IDs only, and must not accept these as qualification evidence.
    return {
        "designId": f"synthetic-{index}", "architectureId": ARCHITECTURES["A"], "strategyId": SR.SPEC_ID,
        "accepted": {"id": f"synthetic-revision-{index}", "privateSource": "/private/must-not-leak.step"},
        "candidate": {"id": "synthetic-preview"} if index % 2 else None,
        "recipe": {"unvalidatedPrivateInput": "/private/recipe.json"}, "recipeHash": "stale-on-purpose",
        "status": "ready", "qualification": {"completeRobot": True},
        "rights": "/private/rights.json", "undo": [{"secret": "/private/history.json"}],
    }


def test_static_catalog_precedes_design_lookup_and_creates_empty_table_without_cad(catalog_case, monkeypatch):
    client, app, settings = catalog_case
    forbid_cad_and_inference(monkeypatch)
    paths = [route.path for route in router.routes]
    assert paths.index("/api/designs/catalog") < paths.index("/api/designs/{design_id}")
    with app.state.store.connect() as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE name='design_realizations'").fetchone() is None
    response = client.get("/api/designs/catalog")
    assert response.status_code == 200, response.text
    expected = {"schemaVersion": 1, "kind": "tachyon.design_catalog", "canGenerateAdditionalArchitectures": False, "saved": [], "architectures": [
        {"architectureId": identity, "alternative": alternative,
         "recipeAvailable": False, "recipeKind": "none", "requestedPlacements": 0,
         "roleIds": [], "qualification": "not_checked"}
        for alternative, identity in ARCHITECTURES.items()
    ]}
    assert response.json() == expected
    assert client.get("/api/designs/catalog").json() == expected
    with app.state.store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM design_realizations").fetchone()[0] == 0
    assert not (settings.data_dir / "catalog").exists()


def test_existing_owner_middleware_protects_catalog_and_prevents_caching(catalog_case):
    client, app, _ = catalog_case
    token = client.headers.pop("X-Tachyon-Session")
    assert client.get("/api/designs/catalog").status_code == 401
    client.headers["X-Tachyon-Session"] = "incorrect-owner"
    assert client.get("/api/designs/catalog").status_code == 401
    client.headers["X-Tachyon-Session"] = token
    assert client.get("/api/designs/catalog", headers={"Origin": "http://127.0.0.1:9001"}).status_code == 403
    response = client.get("/api/designs/catalog")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "private, no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    with app.state.store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM design_realizations").fetchone()[0] == 0


@pytest.mark.parametrize("alternatives", [("A",), ("B",), ("B", "A")])
def test_recipe_availability_counts_actual_requested_members_and_reloads_inputs(catalog_case, monkeypatch, alternatives):
    client, _, settings = catalog_case
    forbid_cad_and_inference(monkeypatch)
    path = write_recipes(settings, [synthetic_recipe(alternative) for alternative in alternatives])
    entries = client.get("/api/designs/catalog").json()["architectures"]
    assert [entry["alternative"] for entry in entries] == ["A", "B"]
    for entry in entries:
        available = entry["alternative"] in alternatives
        assert entry["recipeAvailable"] is available
        assert entry["recipeKind"] == ("authored_component_recipe" if available else "none")
        assert entry["requestedPlacements"] == (2 if available else 0)
        assert entry["roleIds"] == (["chassis", "scorer"] if available else [])
        assert entry["qualification"] == "not_checked"
    path.unlink()
    assert all(not entry["recipeAvailable"] for entry in client.get("/api/designs/catalog").json()["architectures"])


def test_saved_projection_is_bounded_by_insertion_order_private_and_read_only(catalog_case, monkeypatch):
    client, app, settings = catalog_case
    service = store_records(app, settings, [cached_record(index) for index in range(11)])
    # Updating an older row must not masquerade as a newer insertion.
    old = cached_record(0)
    old["accepted"]["id"] = "updated-old-revision"
    with service._database(write=True) as db:
        service._save(db, old)
        before = db.execute("SELECT rowid, id, data FROM design_realizations ORDER BY rowid").fetchall()
    forbid_cad_and_inference(monkeypatch)
    response = client.get("/api/designs/catalog")
    assert response.status_code == 200, response.text
    saved = response.json()["saved"]
    assert [item["designId"] for item in saved] == [f"synthetic-{index}" for index in range(10, 2, -1)]
    for entry, index in zip(saved, range(10, 2, -1)):
        assert entry == {"designId": f"synthetic-{index}", "architectureId": ARCHITECTURES["A"],
                         "strategyId": SR.SPEC_ID, "revisionId": f"synthetic-revision-{index}",
                         "hasCandidate": bool(index % 2)}
    assert "/private/" not in response.text and "completeRobot" not in response.text
    assert "recipeHash" not in response.text and "undo" not in response.text
    assert str(settings.root) not in response.text
    with service._database() as db:
        assert db.execute("SELECT rowid, id, data FROM design_realizations ORDER BY rowid").fetchall() == before


@pytest.mark.parametrize("damage", ["invalid_recipe", "missing_handoff", "changed_handoff"])
def test_unavailable_inputs_do_not_hide_saved_unqualified_builds(catalog_case, monkeypatch, damage):
    client, app, settings = catalog_case
    record = cached_record()
    record["accepted"] = None
    store_records(app, settings, [record])
    if damage == "invalid_recipe":
        recipe = synthetic_recipe()
        recipe["completeRobot"] = True
        write_recipes(settings, [recipe])
    else:
        path = settings.root / SR.HANDOFF / "design/manifest.json"
        if damage == "missing_handoff":
            path.unlink()
        else:
            path.write_bytes(path.read_bytes() + b"\n")
    forbid_cad_and_inference(monkeypatch)
    response = client.get("/api/designs/catalog")
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["saved"]) == 1
    assert data["saved"][0]["revisionId"] is None
    assert data["saved"][0]["hasCandidate"] is False
    assert "qualification" not in data["saved"][0]
    assert all(not entry["recipeAvailable"] for entry in data["architectures"])
    assert bool(data["architectures"]) is (damage == "invalid_recipe")


def test_malformed_saved_metadata_cannot_break_index_or_escape_projection(catalog_case):
    client, app, settings = catalog_case
    service = store_records(app, settings, [cached_record()])
    invalid = deepcopy(cached_record(1))
    invalid["architectureId"] = {"privatePath": "/private/must-not-leak"}
    with service._database(write=True) as db:
        service._save(db, invalid)
        db.execute("INSERT INTO design_realizations VALUES (?, ?)", ("bad-json", "{not JSON"))
    response = client.get("/api/designs/catalog")
    assert response.status_code == 200, response.text
    assert [entry["designId"] for entry in response.json()["saved"]] == ["synthetic-0"]
    assert "/private/" not in response.text


def test_opening_indexed_design_still_requalifies_every_time(catalog_case, monkeypatch):
    client, app, settings = catalog_case
    recipe = R.Recipe.model_validate(synthetic_recipe())
    digest = A.content_hash(recipe.json_data())
    identity = A.stable_id("design", ARCHITECTURES["A"], digest)
    record = {**cached_record(), "designId": identity, "recipe": recipe.json_data(), "recipeHash": digest}
    store_records(app, settings, [record])
    checked = []
    def requalify(self, data, context, current_recipe):
        checked.append(data["designId"])
        raise R.QualificationBlocked([R.missing("catalog", "RIGHTS_UNVERIFIED", "Synthetic revoked-rights response")])
    monkeypatch.setattr(R.RealizationService, "_current", requalify)
    entry = client.get("/api/designs/catalog").json()["saved"][0]
    assert checked == [] and entry["revisionId"] == record["accepted"]["id"]
    for _ in range(2):
        response = client.get(f"/api/designs/{identity}")
        assert response.status_code == 200, response.text
        assert response.json()["accepted"] is None
        assert response.json()["qualification"]["completeRobot"] is False
        assert "RIGHTS_UNVERIFIED" in {gap["code"] for gap in response.json()["missing"]}
    assert checked == [identity, identity]
