"""Real realization/revision HTTP tests using original non-VEX STEP fixtures.

The existing calibration seeder authors the source solids in pytest's temporary
private workspace. Added fixture port measurements and scalar joints exercise
geometry placement, not actual bearings, lift hardware, VEX identity, competition
reach, powered motion or complete-robot acceptance. No user CAD is changed.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import logging
import math
from pathlib import Path
import shutil

from fastapi.testclient import TestClient
import pytest

from fixture_support import FIXTURE_ID, load_json, save_json
from tachyon import assemblies as A, strategy_runtime as SR
from tachyon.app import create_app
from tachyon.cad.prepare import prepare_component
from tachyon.design_api import router
from tachyon.errors import TachyonError
from tachyon.realization import MAX_RECIPE_BYTES, RealizationService, RecipeBook, architecture_context
from tachyon.store import Store


PUBLIC_ROOT = Path(__file__).resolve().parents[2]
PUBLIC = SR.HANDOFF


def install_public_inputs(root):
    for name in ("manifest.json", "design/manifest.json", "design/architecture-proposals.json", "strategy-spec-v2.json"):
        target = root / PUBLIC / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PUBLIC_ROOT / PUBLIC / name, target)


def architecture_id(alternative="B"):
    proposals = load_json(PUBLIC_ROOT / SR.PROPOSALS)
    return next(p["id"] for p in proposals if p["alternative"] == alternative)


def frame_at(point=(0, 0, 0), axis=(0, 0, 1)):
    rotation = A.RigidTransform() if axis == (0, 0, 1) else A.RigidTransform.rotation((1, 0, 0), -math.pi / 2)
    return A.RigidTransform.translation(*point).compose(rotation)


def recipe_for(workspace, kind="prismatic", *, alternative="B"):
    """CLI-seeder helper: private recipe JSON for an original prepared fixture.

    kind: "prismatic" (0/.15 metres) or "revolute" (0/pi/3 radians).
    alternative: "A" or "B"; this binds a partial scorer, never a full design.
    Call prepare_mechanism_fixture(workspace) first. The returned dict is the
    single recipe inside {"schemaVersion": 1, "recipes": [recipe]}.
    """
    if kind not in ("prismatic", "revolute") or alternative not in ("A", "B"):
        raise ValueError("Choose a supported fixture joint kind and A/B alternative")
    key = workspace.component.id
    receipt = workspace.catalog().prepared(workspace.component)
    frames = [{"id": p["id"], "kind": p["kind"], "frame": frame_at(tuple(p["positionM"]), tuple(p["axis"])).json_data(),
               "frameBasis": "measured", "evidence": p["evidence"]} for p in receipt["ports"]]
    port = "slide" if kind == "prismatic" else "hinge"
    q = .15 if kind == "prismatic" else math.pi / 3
    point = [.12, .20, 0] if kind == "prismatic" else [.12 * math.cos(q) - .05 * math.sin(q), .12 * math.sin(q) + .05 * math.cos(q), 0]
    return {"id": "original-joint-fixture-" + kind, "alternative": alternative, "roleComponentIds": {"scorer": [key]},
            "portFrames": {key: {"sourceSha256": workspace.component.source_sha256, "ports": frames}},
            "template": {"rootInstanceId": "base", "subsystems": [{"id": "scorer", "name": "Original partial scorer test fixture"}],
                         "instances": [{"id": "base", "componentId": key, "subsystemId": "scorer"},
                                       {"id": "carrier", "componentId": key, "subsystemId": "scorer", "parentId": "base"},
                                       {"id": "tip", "componentId": key, "subsystemId": "scorer", "parentId": "carrier"}],
                         "relationships": [{"id": "lift", "parentInstanceId": "base", "parentPortId": port,
                                            "childInstanceId": "carrier", "childPortId": port, "kind": kind,
                                            "axis": [0, 0, 1], "limits": [0, .2 if kind == "prismatic" else 1.2],
                                            "movingMemberIds": ["carrier", "tip"]},
                                           {"id": "tip-mount", "parentInstanceId": "carrier", "parentPortId": "out",
                                            "childInstanceId": "tip", "childPortId": "mount"}]},
            "actions": [{"actionId": "place_alliance", "subsystemId": "scorer", "instanceIds": ["carrier", "tip"],
                         "jointIds": ["lift"], "anchors": [{"id": "tool", "instanceId": "tip", "localPointM": [.02, .03, 0]}]}],
            "configurations": {"lower": {"jointPositions": {"lift": 0}, "reach": {"actionId": "place_alliance", "anchorId": "tool",
                                                                                       "worldPointM": [.12, .05, 0], "evidence": "Original fixture anchor only"}},
                               "raised": {"jointPositions": {"lift": q}, "reach": {"actionId": "place_alliance", "anchorId": "tool",
                                                                                       "worldPointM": point, "evidence": "Derived fixture pose; no physical reach qualification"}}}}


def write_recipe(workspace, recipe):
    path = workspace.data_dir / "catalog/assembly-recipes.json"
    save_json(path, {"schemaVersion": 1, "recipes": [recipe]})
    return path


def prepare_mechanism_fixture(workspace):
    """Prepare port metadata/receipts for fixture_support's original STEP only.

    Seeder usage (from the repo root with server/tests on sys.path)::

        w = create_calibration_workspace(root, private_data_dir)
        prepare_mechanism_fixture(w)
        write_recipe(w, recipe_for(w, kind="prismatic", alternative="B"))

    The fixture generator creates its own self-authorship evidence. This helper
    does not change that evidence or source geometry and refuses nonfixtures.
    """
    w = workspace
    if (w.component.id != FIXTURE_ID or w.component.origin_kind != "tachyon_authored"
            or w.component.geometry_class != "test_fixture"):
        raise ValueError("Only the original fixture_support calibration workspace is supported")
    manifest = load_json(w.manifest_path)
    manifest["components"][0]["ports"] = [
        {"id": "slide", "kind": "prismatic", "positionM": [0, 0, 0], "axis": [0, 1, 0], "evidence": "Original fixture slide reference; computational test only"},
        {"id": "hinge", "kind": "revolute", "positionM": [0, 0, 0], "axis": [0, 0, 1], "evidence": "Original fixture hinge reference; computational test only"},
        {"id": "out", "kind": "mount", "positionM": [.1, .02, 0], "axis": [0, 0, 1], "evidence": "Authored frame reference offset, not physical mount qualification"},
        {"id": "mount", "kind": "mount", "positionM": [0, 0, 0], "axis": [0, 0, 1], "evidence": "Original fixture origin reference only"}]
    save_json(w.manifest_path, manifest)
    prepare_component(w.catalog(), w.component)
    return w


@pytest.fixture
def realization_workspace(prepared_workspace):
    install_public_inputs(prepared_workspace.settings.root)
    return prepare_mechanism_fixture(prepared_workspace)


@pytest.fixture
def design_case(realization_workspace, caplog):
    caplog.set_level(logging.ERROR, logger="uvicorn.error")
    w = realization_workspace
    recipe = recipe_for(w)
    write_recipe(w, recipe)
    app = create_app(w.settings)
    # Main owns production wiring; include here solely to test this router.
    if not any(getattr(route, "path", None) == "/api/designs/realize" for route in app.routes):
        app.include_router(router)
    with TestClient(app, base_url=w.settings.ui_origin, client=("127.0.0.1", 50000)) as client:
        client.headers["X-Tachyon-Session"] = app.state.session
        yield client, w, recipe


def post_realize(client):
    response = client.post("/api/designs/realize", json={"architecture_id": architecture_id()})
    assert response.status_code == 200, response.text
    return response.json()


def preview(client, initial, configuration="raised"):
    response = client.post(f'/api/designs/{initial["designId"]}/preview', json={
        "base_revision_id": initial["revisionId"], "configuration_id": configuration})
    assert response.status_code == 200, response.text
    return response.json()


def decision(client, session, action, candidate=None, base=None):
    body = {"base_revision_id": base or session["revisionId"], "action": action}
    if candidate is not None:
        body["candidate_revision_id"] = candidate
    return client.post(f'/api/designs/{session["designId"]}/decision', json=body)


def assert_partial(session):
    assert session["status"] == "partial", [m for m in session["missing"] if m["code"] != "REQUIRED_ROLE_UNREALIZED"]
    assert session["qualification"]["completeRobot"] is False
    assert session["qualification"]["hardwareQualified"] is False
    assert session["qualification"]["capabilityStatus"] == "unverified"
    assert session["qualification"]["testFixtureOnly"] is True
    assert set(session["plan"]["requiredRoles"]) == {"chassis", "drive", "pin_intake", "pin_transfer", "scorer", "cup_cradle", "stack_interface"}
    assert {r["role"] for r in session["missing"] if r["code"] == "REQUIRED_ROLE_UNREALIZED"} == set(session["plan"]["requiredRoles"]) - {"scorer"}
    assert "TEST_FIXTURE_ONLY" in {r["code"] for r in session["missing"]}


def assert_blocked(response, code):
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "blocked" and not data["canEdit"]
    assert code in {row["code"] for row in data["missing"]}
    for field in ("accepted", "candidate", "bindings", "candidateBindings", "revisionId"):
        assert data[field] is None
    assert data["worldTransforms"] == data["candidateWorldTransforms"] == {}
    assert data["components"] == [] and isinstance(data["plan"], dict)
    assert data["qualification"]["completeRobot"] is False
    return data


@pytest.mark.parametrize("kind", ["prismatic", "revolute"])
def test_original_step_true_joint_poses_descendants_anchors_and_full_receipts(design_case, kind):
    client, w, _ = design_case
    recipe = recipe_for(w, kind)
    write_recipe(w, recipe)
    initial = post_realize(client)
    assert_partial(initial)
    assert initial["canEdit"] is True
    assert initial["candidateWorldTransforms"] == {} and initial["candidate"] is None
    assert len(initial["components"]) == 1
    full = initial["components"][0]
    for field in ("boundsM", "nativeHierarchy", "meshUrl", "sourceSha256", "meshSha256", "catalogFingerprint", "geometryValidation"):
        assert field in full
    assert full["geometryClass"] == "test_fixture" and full["completeRobot"] is False
    assert client.get(full["meshUrl"]).status_code == 200
    raised = preview(client, initial)
    assert raised["accepted"] == initial["accepted"] and raised["bindings"] == initial["bindings"]
    assert raised["candidate"]["parentRevisionId"] == initial["revisionId"]
    assert raised["candidate"]["engineeringHash"] != initial["accepted"]["engineeringHash"]
    assert raised["candidateBindings"]["strategyId"] == SR.SPEC_ID
    assert raised["candidateBindings"]["competitionId"] == SR.COMPETITION_ID
    assert raised["candidateBindings"]["revisionId"] == raised["candidate"]["id"]
    assert {n["id"] for n in raised["accepted"]["assembly"]["instances"]} == {n["id"] for n in raised["candidate"]["assembly"]["instances"]}
    assert raised["candidateBindings"]["definitions"] == raised["bindings"]["definitions"]
    assert raised["candidateBindings"]["actions"][0]["anchors"][0]["id"] == raised["bindings"]["actions"][0]["anchors"][0]["id"]
    point = raised["candidateBindings"]["actions"][0]["anchors"][0]["worldPointM"]
    assert point == pytest.approx(recipe["configurations"]["raised"]["reach"]["worldPointM"])
    if kind == "prismatic":
        assert raised["candidateWorldTransforms"]["carrier"][13] == pytest.approx(.15)
        assert raised["candidateWorldTransforms"]["tip"][13] == pytest.approx(.17)
    else:
        assert raised["candidateWorldTransforms"]["carrier"][0] == pytest.approx(.5)
        assert raised["candidateWorldTransforms"]["tip"][12] == pytest.approx(.1 * .5 - .02 * math.sin(math.pi / 3))
        assert raised["candidateWorldTransforms"]["tip"][13] == pytest.approx(.1 * math.sin(math.pi / 3) + .02 * .5)
    annotation = raised["candidateAnnotations"][0]
    assert annotation["anchor"]["worldPointM"] == pytest.approx(point)
    assert {"base", "carrier", "tip", "lift", "tip-mount", w.component.id} <= set(annotation["dependencyIds"])
    assert annotation["revisionId"] == raised["candidate"]["id"]
    for field in ("accepted", "candidate"):
        assert A.validate_revision(A.AssemblyRevision.model_validate(raised[field])).graph_valid


def test_sqlite_preview_apply_idempotence_discard_and_compensating_undo(design_case):
    client, w, _ = design_case
    initial = post_realize(client)
    first = preview(client, initial)
    # Independent service instance sees the stored preview, not a reconstruction.
    restarted = RealizationService(w.settings, Store(w.data_dir)).read(initial["designId"])
    assert restarted == first
    discarded = decision(client, initial, "discard")
    assert discarded.status_code == 200
    assert discarded.json()["accepted"] == initial["accepted"]
    assert discarded.json()["candidate"] is None and discarded.json()["candidateWorldTransforms"] == {}
    pending = preview(client, initial)
    candidate_id = pending["candidate"]["id"]
    applied = decision(client, initial, "apply", candidate_id)
    assert applied.status_code == 200, applied.text
    current = applied.json()
    assert current["accepted"] == pending["candidate"] and current["bindings"] == pending["candidateBindings"]
    assert current["previous"] == initial["accepted"]
    assert decision(client, initial, "apply", candidate_id).json() == current
    assert client.get(f'/api/designs/{initial["designId"]}').json() == current
    undone = decision(client, current, "undo")
    assert undone.status_code == 200, undone.text
    restored = undone.json()
    assert restored["accepted"]["engineeringHash"] == initial["accepted"]["engineeringHash"]
    assert restored["revisionId"] != initial["revisionId"]
    assert restored["accepted"]["parentRevisionId"] == current["revisionId"]
    assert restored["worldTransforms"] == initial["worldTransforms"]
    assert restored["bindings"]["revisionId"] == restored["revisionId"]
    assert restored["annotations"][0]["id"] == initial["annotations"][0]["id"]
    assert restored["annotations"][0]["revisionId"] == restored["revisionId"]
    assert restored["previous"] is None
    assert decision(client, restored, "undo").json()["code"] == "UNDO_UNAVAILABLE"
    assert RealizationService(w.settings, Store(w.data_dir)).read(initial["designId"]) == restored


def test_multiple_undo_walks_history_without_turning_into_redo(design_case):
    client, _, _ = design_case
    initial = post_realize(client)
    raised = preview(client, initial)
    one = decision(client, initial, "apply", raised["candidate"]["id"]).json()
    lower = preview(client, one, "lower")
    two = decision(client, one, "apply", lower["candidate"]["id"]).json()
    undo_one = decision(client, two, "undo").json()
    assert undo_one["accepted"]["engineeringHash"] == one["accepted"]["engineeringHash"]
    undo_two = decision(client, undo_one, "undo").json()
    assert undo_two["accepted"]["engineeringHash"] == initial["accepted"]["engineeringHash"]
    assert undo_two["revisionId"] != initial["revisionId"]
    assert decision(client, undo_two, "undo").status_code == 409


def test_stale_and_wrong_candidate_guards_never_overwrite_accepted(design_case):
    client, _, _ = design_case
    initial = post_realize(client)
    pending = preview(client, initial)
    assert decision(client, initial, "apply").status_code == 409
    assert decision(client, initial, "discard", "wrong-candidate").json()["code"] == "CANDIDATE_CONFLICT"
    current = decision(client, initial, "apply", pending["candidate"]["id"]).json()
    stale = client.post(f'/api/designs/{initial["designId"]}/preview', json={"base_revision_id": initial["revisionId"], "configuration_id": "lower"})
    assert stale.status_code == 409 and stale.json()["code"] == "REVISION_CONFLICT"
    assert decision(client, initial, "undo").status_code == 409
    assert client.get(f'/api/designs/{initial["designId"]}').json() == current


def test_concurrent_apply_and_discard_serialize_candidate_decision(design_case):
    client, w, _ = design_case
    initial = post_realize(client)
    pending = preview(client, initial)
    def run(action):
        service = RealizationService(w.settings, Store(w.data_dir))
        try:
            return service.decide(initial["designId"], initial["revisionId"], action, pending["candidate"]["id"])
        except TachyonError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, ("apply", "discard")))
    assert sum(isinstance(result, dict) for result in results) == 1
    current = client.get(f'/api/designs/{initial["designId"]}').json()
    assert current["candidate"] is None
    assert current["accepted"] in (initial["accepted"], pending["candidate"])


@pytest.mark.parametrize("mutation,code", [
    ("source", "SOURCE_HASH_MISMATCH"), ("mesh", "MESH_HASH_MISMATCH"),
    ("rights", "SOURCE_NOT_QUALIFIED"), ("evidence", "RIGHTS_EVIDENCE_CHANGED"),
    ("reference", "REFERENCE_ONLY_COMPONENT"), ("quality", "GEOMETRY_NOT_QUALIFIED"),
    ("catalog", "MISSING_COMPONENT"), ("recipe", "RECIPE_CHANGED"),
])
def test_current_versions_and_rights_rechecked_for_read_apply_and_undo(design_case, mutation, code):
    client, w, recipe = design_case
    initial = post_realize(client)
    pending = preview(client, initial)
    applied = decision(client, initial, "apply", pending["candidate"]["id"]).json()
    lower = preview(client, applied, "lower")
    before_db = Store(w.data_dir)
    with before_db.connect() as db:
        before = db.execute("SELECT data FROM design_realizations WHERE id=?", (initial["designId"],)).fetchone()[0]
    if mutation == "source":
        # Never rewrite user geometry: only the existing authored temp fixture.
        w.source_path.write_bytes(w.source_path.read_bytes() + b"\n/* test-only changed source */\n")
    elif mutation == "mesh":
        receipt = load_json(w.catalog().receipt_path(w.component))
        (w.data_dir / "meshes" / (receipt["meshSha256"] + ".glb")).write_bytes(b"changed-test-only-mesh")
    elif mutation == "rights":
        w.update_permission("assembly_placement", status="unverified")
    elif mutation == "evidence":
        w.evidence_path.write_text("Test-only evidence changed; no rights granted")
    elif mutation == "reference":
        w.update_component(referenceOnly=True)
    elif mutation == "quality":
        path = w.catalog().receipt_path(w.component)
        receipt = load_json(path)
        receipt["geometryValidation"]["qualifiedForRobotGeneration"] = False
        save_json(path, receipt)
    elif mutation == "catalog":
        save_json(w.manifest_path, {"schemaVersion": 1, "components": []})
    else:
        recipe["id"] = "changed-private-recipe"
        write_recipe(w, recipe)
    assert_blocked(client.get(f'/api/designs/{initial["designId"]}'), code)
    assert_blocked(decision(client, applied, "apply", lower["candidate"]["id"]), code)
    assert_blocked(decision(client, applied, "undo"), code)
    with before_db.connect() as db:
        after = db.execute("SELECT data FROM design_realizations WHERE id=?", (initial["designId"],)).fetchone()[0]
    assert before == after


def test_inspection_references_with_no_ports_and_unverified_rights_remain_blocked(design_case):
    client, w, recipe = design_case
    # Original fixture metadata models the *restrictions* of today's catalog;
    # it is never used as a substitute for the real 450-solid reference.
    w.update_component(referenceOnly=True, ports=[])
    w.update_permission("assembly_placement", status="unverified")
    result = assert_blocked(client.post("/api/designs/realize", json={"architecture_id": architecture_id()}), "REFERENCE_ONLY_COMPONENT")
    codes = {r["code"] for r in result["missing"]}
    assert {"MISSING_PORT", "SOURCE_NOT_QUALIFIED"} <= codes
    assert not result["components"]
    (w.data_dir / "catalog/assembly-recipes.json").unlink()
    result = assert_blocked(client.post("/api/designs/realize", json={"architecture_id": architecture_id()}), "ASSEMBLY_RECIPE_MISSING")
    assert {r["role"] for r in result["missing"] if r["code"] == "REQUIRED_ROLE_UNREALIZED"} == set(result["plan"]["requiredRoles"])


@pytest.mark.parametrize("mutate,code", [
    (lambda r: r.update(portFrames={}), "MISSING_PORT_FRAMES"),
    (lambda r: r["template"]["relationships"][0].update(parentPortId="nonexistent"), "MISSING_PORT"),
    (lambda r: next(iter(r["portFrames"].values())).update(sourceSha256="9" * 64), "STALE_PORT_FRAMES"),
    (lambda r: next(iter(r["portFrames"].values()))["ports"][0]["frame"]["matrix"].__setitem__(12, .1), "PORT_FRAME_MISMATCH"),
    (lambda r: r["actions"][0].update(actionId="fabricated-action"), "INVALID_STRATEGY_BINDING"),
    (lambda r: r["actions"][0].update(subsystemId="drive"), "INVALID_BINDING"),
    (lambda r: r["configurations"]["lower"]["reach"].update(worldPointM=[100, 100, 100]), "REACH_ANCHOR_MISMATCH"),
])
def test_precise_recipe_port_and_binding_blockers_without_placeholder_geometry(design_case, mutate, code):
    client, w, recipe = design_case
    mutate(recipe)
    write_recipe(w, recipe)
    assert_blocked(client.post("/api/designs/realize", json={"architecture_id": architecture_id()}), code)


@pytest.mark.parametrize("mutate", [
    lambda r: r.update(completeRobot=True),
    lambda r: r.update(qualifiedOperations=["assembly_placement"]),
    lambda r: r["template"]["instances"][0].update(transform=A.RigidTransform.translation(0, 1, 0).json_data()),
    lambda r: r["configurations"]["raised"].update(transforms={"carrier": A.RigidTransform.translation(0, .15, 0).json_data()}),
    lambda r: r["configurations"]["raised"]["jointPositions"].update(lift="0.15"),
    lambda r: r["configurations"]["raised"]["jointPositions"].update(lift=True),
    lambda r: r["configurations"]["raised"]["jointPositions"].update(**{"tip-mount": .15}),
    lambda r: r["template"]["instances"].append(r["template"]["instances"][0]),
    lambda r: r["portFrames"][next(iter(r["portFrames"]))]["ports"][0].update(frameBasis="axis_only"),
])
def test_strict_private_recipe_cannot_supply_rights_readiness_static_pose_or_coercions(design_case, mutate):
    client, w, recipe = design_case
    mutate(recipe)
    write_recipe(w, recipe)
    assert_blocked(client.post("/api/designs/realize", json={"architecture_id": architecture_id()}), "INVALID_ASSEMBLY_RECIPES")


def test_recipe_size_duplicate_keys_and_symlink_escape_are_rejected(design_case, tmp_path):
    client, w, _ = design_case
    path = w.data_dir / "catalog/assembly-recipes.json"
    for contents in (b" " * (MAX_RECIPE_BYTES + 1), b'{"recipes":[],"recipes":[]}', b'{"recipes":[],"schemaVersion":NaN}'):
        path.write_bytes(contents)
        assert_blocked(client.post("/api/designs/realize", json={"architecture_id": architecture_id()}), "INVALID_ASSEMBLY_RECIPES")
    path.unlink()
    outside = tmp_path / "outside-private-root.json"
    outside.write_text('{"recipes":[]}')
    path.symlink_to(outside)
    assert_blocked(client.post("/api/designs/realize", json={"architecture_id": architecture_id()}), "INVALID_LOCAL_PATH")


@pytest.mark.parametrize("kind", ["prismatic", "revolute"])
def test_non_tree_constraint_closure_is_rechecked_at_each_joint_pose(design_case, kind):
    client, w, _ = design_case
    recipe = recipe_for(w, kind)
    recipe["template"]["relationships"].append({"id": "closed-brace", "parentInstanceId": "base", "parentPortId": "out",
                                                     "childInstanceId": "tip", "childPortId": "mount"})
    write_recipe(w, recipe)
    session = post_realize(client)
    assert_partial(session)
    assert session["canEdit"] is False
    assert "PORT_ALIGNMENT" in {m["code"] for m in session["missing"]}
    response = client.post(f'/api/designs/{session["designId"]}/preview', json={"base_revision_id": session["revisionId"], "configuration_id": "raised"})
    assert response.status_code == 422 and response.json()["code"] == "UNSUPPORTED_CONFIGURATION"
    assert client.get(f'/api/designs/{session["designId"]}').json()["candidate"] is None


@pytest.mark.parametrize("change,code", [("same", "DISTINCT_JOINT_POSES_REQUIRED"), ("reach", "REACH_ANCHOR_MISMATCH"),
                                         ("missing", "DISTINCT_REACH_REQUIRED"), ("limit", "INVALID_JOINT_CONFIGURATION")])
def test_two_names_bad_reach_or_out_of_limit_joint_do_not_enable_edit(design_case, change, code):
    client, w, recipe = design_case
    if change == "same":
        recipe["configurations"]["raised"] = deepcopy(recipe["configurations"]["lower"])
    elif change == "reach":
        recipe["configurations"]["raised"]["reach"]["worldPointM"] = [0, 10, 0]
    elif change == "missing":
        recipe["configurations"]["raised"].pop("reach")
    else:
        recipe["configurations"]["raised"]["jointPositions"]["lift"] = .3
    write_recipe(w, recipe)
    session = post_realize(client)
    assert_partial(session)
    assert not session["canEdit"]
    assert code in {row["code"] for row in session["missing"]}


def test_unsupported_configuration_validation_retains_saved_candidate(design_case):
    client, _, _ = design_case
    initial = post_realize(client)
    pending = preview(client, initial)
    response = client.post(f'/api/designs/{initial["designId"]}/preview', json={"base_revision_id": initial["revisionId"], "configuration_id": "infinite-lift"})
    assert response.status_code == 422
    assert client.get(f'/api/designs/{initial["designId"]}').json() == pending


def test_raised_label_cannot_move_the_scoring_anchor_down(design_case):
    client, w, recipe = design_case
    recipe["configurations"]["lower"], recipe["configurations"]["raised"] = recipe["configurations"]["raised"], recipe["configurations"]["lower"]
    write_recipe(w, recipe)
    session = post_realize(client)
    assert not session["canEdit"]
    assert "RAISED_HEIGHT_REQUIRED" in {m["code"] for m in session["missing"]}


def test_scoring_height_edit_cannot_change_an_independent_drive_joint(design_case):
    client, w, recipe = design_case
    key = w.component.id
    recipe["roleComponentIds"]["drive"] = [key]
    recipe["template"]["subsystems"].append({"id": "drive", "name": "Independent drive fixture"})
    recipe["template"]["instances"].append({"id": "wheel", "componentId": key, "subsystemId": "drive", "parentId": "base"})
    recipe["template"]["relationships"].append({"id": "wheel-spin", "parentInstanceId": "base", "parentPortId": "hinge",
        "childInstanceId": "wheel", "childPortId": "hinge", "kind": "revolute", "axis": [0, 0, 1],
        "limits": [0, 1], "movingMemberIds": ["wheel"]})
    recipe["configurations"]["lower"]["jointPositions"]["wheel-spin"] = 0
    recipe["configurations"]["raised"]["jointPositions"]["wheel-spin"] = .1
    write_recipe(w, recipe)
    session = post_realize(client)
    assert not session["canEdit"]
    assert "EDIT_SCOPE_VIOLATION" in {m["code"] for m in session["missing"]}


@pytest.mark.parametrize("target", ["accepted", "candidate", "history", "bindings", "candidateBindings"])
def test_saved_hash_and_exact_revision_binding_tampering_never_reaches_renderer(design_case, target):
    client, w, _ = design_case
    initial = post_realize(client)
    pending = preview(client, initial)
    current = decision(client, initial, "apply", pending["candidate"]["id"]).json()
    preview(client, current, "lower")
    with Store(w.data_dir).connect() as db:
        raw = json.loads(db.execute("SELECT data FROM design_realizations WHERE id=?", (initial["designId"],)).fetchone()[0])
        if target == "history":
            raw["undo"][0]["revision"]["engineeringHash"] = "0" * 64
        elif target in ("bindings", "candidateBindings"):
            raw[target]["actions"][0]["anchors"][0]["worldPointM"][1] += 1
        else:
            raw[target]["engineeringHash"] = "0" * 64
        db.execute("UPDATE design_realizations SET data=? WHERE id=?", (json.dumps(raw), initial["designId"]))
    response = client.get(f'/api/designs/{initial["designId"]}')
    assert response.status_code in (409, 422)
    assert response.json()["code"] in {"REVISION_HASH_MISMATCH", "BINDINGS_HASH_MISMATCH"}
    assert "accepted" not in response.json()


@pytest.mark.parametrize("relative", ["design/architecture-proposals.json", "manifest.json", "design/manifest.json", "strategy-spec-v2.json"])
def test_fixed_architecture_dataset_manifest_checksums_are_mandatory(design_case, relative):
    client, w, _ = design_case
    initial = post_realize(client)
    path = w.settings.root / SR.HANDOFF / relative
    path.write_bytes(path.read_bytes() + b" ")
    for response in (client.post("/api/designs/realize", json={"architecture_id": architecture_id()}),
                     client.get(f'/api/designs/{initial["designId"]}')):
        assert response.status_code == 503
        assert response.json()["code"] == "ARCHITECTURE_DATASET_UNVERIFIED"


def test_architecture_ids_are_exact_and_context_is_the_real_strategy(design_case):
    client, w, _ = design_case
    assert client.post("/api/designs/realize", json={"architecture_id": "B"}).status_code == 404
    context = architecture_context(w.settings.root, architecture_id())
    assert context.spec["id"] == SR.SPEC_ID
    assert len(context.roles) == 7
    assert len(RecipeBook.model_json_schema()["$defs"]) > 10
    # An unrelated alternative never borrows a whole reference or B's scorer.
    blocked = client.post("/api/designs/realize", json={"architecture_id": architecture_id("A")})
    assert_blocked(blocked, "ASSEMBLY_RECIPE_MISSING")
    assert blocked.json()["plan"]["subsystems"][4]["mechanismIntent"] == "four_bar_gripper"


def test_blocked_designs_persist_recheck_inputs_and_require_explicit_realization(design_case):
    client, w, _ = design_case
    w.update_permission("assembly_placement", status="unverified")
    blocked = assert_blocked(client.post("/api/designs/realize", json={"architecture_id": architecture_id()}), "SOURCE_NOT_QUALIFIED")
    path = f'/api/designs/{blocked["designId"]}'
    assert_blocked(client.get(path), "SOURCE_NOT_QUALIFIED")
    w.update_permission("assembly_placement", status="qualified")
    # Reading may diagnose availability but cannot create an accepted revision.
    assert_blocked(client.get(path), "REALIZATION_REQUIRED")
    realized = post_realize(client)
    assert_partial(realized)
    assert realized["designId"] == blocked["designId"]
    assert client.get(path).json() == realized
    # Failed re-realization cannot replace an accepted snapshot with null state.
    w.update_permission("assembly_placement", status="unverified")
    assert_blocked(client.post("/api/designs/realize", json={"architecture_id": architecture_id()}), "SOURCE_NOT_QUALIFIED")
    w.update_permission("assembly_placement", status="qualified")
    assert client.get(path).json() == realized


def test_missing_recipe_observation_persists_without_adopting_another_recipe(design_case):
    client, w, recipe = design_case
    path = w.data_dir / "catalog/assembly-recipes.json"
    path.unlink()
    blocked = assert_blocked(client.post("/api/designs/realize", json={"architecture_id": architecture_id()}), "ASSEMBLY_RECIPE_MISSING")
    assert_blocked(client.get(f'/api/designs/{blocked["designId"]}'), "ASSEMBLY_RECIPE_MISSING")
    write_recipe(w, recipe)
    assert_blocked(client.get(f'/api/designs/{blocked["designId"]}'), "RECIPE_CHANGED")
    session = post_realize(client)
    assert session["designId"] != blocked["designId"]
    assert_partial(session)


def test_even_all_seven_roles_in_a_fixture_graph_remain_partial(design_case):
    client, w, recipe = design_case
    for role in ("chassis", "drive", "pin_intake", "pin_transfer", "cup_cradle", "stack_interface"):
        recipe["roleComponentIds"][role] = [w.component.id]
        recipe["template"]["subsystems"].append({"id": role, "name": "Original test fixture for " + role})
        recipe["template"]["instances"].append({"id": role, "componentId": w.component.id, "subsystemId": role, "parentId": "base"})
        recipe["template"]["relationships"].append({"id": role + "-mount", "parentInstanceId": "base", "parentPortId": "out",
                                                       "childInstanceId": role, "childPortId": "mount"})
    write_recipe(w, recipe)
    session = post_realize(client)
    assert session["status"] == "partial" and session["canEdit"]
    assert session["qualification"]["completeRobot"] is False
    assert not any(row["code"] == "REQUIRED_ROLE_UNREALIZED" for row in session["missing"])
    assert {"TEST_FIXTURE_ONLY", "HARDWARE_QUALIFICATION_INCOMPLETE"} <= {row["code"] for row in session["missing"]}


def test_measured_child_frame_roll_is_inverted_and_descendant_port_anchor_recomputed(design_case):
    client, w, recipe = design_case
    frames = recipe["portFrames"][w.component.id]["ports"]
    mount = next(port for port in frames if port["id"] == "mount")
    mount["frame"] = A.RigidTransform.rotation((0, 0, 1), math.pi / 4).json_data()
    # The declared child roll changes its local orientation while preserving the
    # registered origin and +Z. Anchor the descendant's actual measured port.
    recipe["actions"][0]["anchors"] = [{"id": "tool", "instanceId": "tip", "portId": "out"}]
    expected = A.RigidTransform.translation(.1, .02, 0).compose(A.RigidTransform.rotation((0, 0, 1), -math.pi / 4)).point((.1, .02, 0))
    recipe["configurations"]["lower"]["reach"]["worldPointM"] = list(expected)
    recipe["configurations"]["raised"]["reach"]["worldPointM"] = [expected[0], expected[1] + .15, expected[2]]
    write_recipe(w, recipe)
    initial = post_realize(client)
    assert_partial(initial)
    raised = preview(client, initial)
    assert raised["worldTransforms"]["tip"][0] == pytest.approx(math.sqrt(.5))
    assert raised["candidateAnnotations"][0]["anchor"]["worldPointM"] == pytest.approx([expected[0], expected[1] + .15, expected[2]])


def test_router_uses_owner_session_and_does_not_leak_paths(design_case):
    client, w, _ = design_case
    initial = post_realize(client)
    assert client.get(f'/api/designs/{initial["designId"]}').headers["Cache-Control"] == "private, no-store"
    client.headers.pop("X-Tachyon-Session")
    assert client.post("/api/designs/realize", json={"architecture_id": architecture_id()}).status_code == 401
    assert str(w.data_dir) not in json.dumps(initial)


def test_reach_diagnostic_compares_actual_anchor_to_learned_target_without_certifying_hardware(design_case):
    client, _, _ = design_case
    initial = post_realize(client)
    assert initial["qualification"]["modeledReachTargetM"] == pytest.approx(.352)
    assert initial["qualification"]["reach"]["heightM"] == pytest.approx(.05)
    assert initial["qualification"]["anchorHeightMeetsModeledTarget"] is False
    assert "MODELED_REACH_TARGET_UNMET" in {m["code"] for m in initial["missing"]}
    raised = preview(client, initial)
    assert raised["qualification"]["candidateReach"]["heightM"] == pytest.approx(.20)
    assert raised["qualification"]["physicalPerformanceVerified"] is False
    assert raised["qualification"]["completeRobot"] is False
