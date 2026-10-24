"""Owner-local manual assembly drafts; never live AI or robot-readiness claims."""
import json
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field

from . import assemblies as A, bindings as B
from .cad.catalog import Catalog
from .errors import TachyonError
from .models import Model, Operation

router = APIRouter(prefix="/api/assembly-drafts")


class CreateDraft(Model):
    design_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    root_instance_id: str
    configuration_id: str = "initial"
    instances: list[A.ComponentInstance]
    subsystems: list[A.Subsystem]
    relationships: list[A.Relationship]
    actions: list[B.ActionBinding] = Field(default_factory=list)


class Remount(Model):
    base_revision_id: str
    relationship_id: str
    parent_port_id: str
    configuration_id: str


class Decision(Model):
    action: Literal["apply", "discard", "undo"]
    base_revision_id: str
    candidate_revision_id: str | None = None


def _database(request):
    db = request.app.state.store.connect()
    db.execute("CREATE TABLE IF NOT EXISTS assembly_drafts (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
    db.commit()
    return db


def _load(db, design_id):
    row = db.execute("SELECT data FROM assembly_drafts WHERE id = ?", (design_id,)).fetchone()
    if row is None:
        raise TachyonError("ASSEMBLY_DRAFT_MISSING", "This local assembly draft does not exist", 404)
    return json.loads(row[0])


def _service(request, component_ids):
    # Geometry is resolved from the current private catalog. Request bodies never
    # supply assets, permission labels, geometry classes or invented source hashes.
    catalog = Catalog(request.app.state.settings)
    from .app import is_lan
    definitions = []
    for key in sorted(set(component_ids)):
        component = next((c for c in catalog.manifest.components if c.id == key), None)
        if component is None:
            raise TachyonError("MISSING_COMPONENT", "An assembly component is unavailable")
        prepared = catalog.prepared(component, lan=is_lan(request))
        if prepared.get("referenceOnly"):
            raise TachyonError("REFERENCE_ONLY_COMPONENT", "Imported inspection references are not qualified design components")
        catalog.policy.require(component.source_sha256, [Operation.assembly_placement])
        definitions.append(A.ComponentDefinition.from_prepared(prepared, qualified_operations=("assembly_placement",)))
    return A.AssemblyService(definitions)


def _reply(data):
    accepted = A.AssemblyRevision.model_validate(data["accepted"])
    candidate = A.AssemblyRevision.model_validate(data["candidate"]) if data.get("candidate") else None
    return {**data, "kind": "manual_assembly_draft", "aiGenerated": False,
            "readiness": A.validate_revision(accepted).json_data(),
            "worldTransforms": {key: list(pose.matrix) for key, pose in A.world_transforms(accepted.assembly).items()},
            "candidateWorldTransforms": {key: list(pose.matrix) for key, pose in A.world_transforms(candidate.assembly).items()} if candidate else None}


def _save(db, design_id, data):
    db.execute("UPDATE assembly_drafts SET data = ? WHERE id = ?", (json.dumps(data), design_id))


@router.post("")
def create(body: CreateDraft, request: Request):
    service = _service(request, [node.component_id for node in body.instances])
    revision = service.build(design_id=body.design_id, recipe_id="manual-declared-attachments-v1",
                             configuration_id=body.configuration_id, root_instance_id=body.root_instance_id,
                             instances=body.instances, subsystems=body.subsystems, relationships=body.relationships)
    links = B.bind_actions(revision, competition_id="unqualified-manual-context", strategy_id="manual-actions", actions=body.actions)
    data = {"accepted": revision.json_data(), "bindings": links.json_data(),
            "candidate": None, "candidateBindings": None, "previous": None, "previousBindings": None}
    with _database(request) as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM assembly_drafts WHERE id = ?", (body.design_id,)).fetchone():
            raise TachyonError("ASSEMBLY_DRAFT_EXISTS", "Choose a new draft identity; existing work is retained", 409)
        db.execute("INSERT INTO assembly_drafts VALUES (?, ?)", (body.design_id, json.dumps(data)))
    return _reply(data)


@router.get("/{design_id}")
def read(design_id: str, request: Request):
    with _database(request) as db:
        data = _load(db, design_id)
    revision = A.AssemblyRevision.model_validate(data["accepted"])
    _service(request, [c.id for c in revision.assembly.components]).validate(revision)
    return _reply(data)


@router.post("/{design_id}/preview")
def preview(design_id: str, body: Remount, request: Request):
    with _database(request) as db:
        db.execute("BEGIN IMMEDIATE")
        data = _load(db, design_id)
        revision = A.AssemblyRevision.model_validate(data["accepted"])
        if revision.id != body.base_revision_id:
            raise TachyonError("REVISION_CONFLICT", "The accepted assembly changed; refresh before previewing", 409)
        service = _service(request, [c.id for c in revision.assembly.components])
        service.validate(revision)
        candidate = service.align_ports(revision, body.relationship_id, parent_port_id=body.parent_port_id,
                                        configuration_id=body.configuration_id)
        links = B.rebind_actions(candidate, B.BindingSnapshot.model_validate(data["bindings"]))
        data.update(candidate=candidate.json_data(), candidateBindings=links.json_data())
        _save(db, design_id, data)
    return _reply(data)


@router.post("/{design_id}/decision")
def decide(design_id: str, body: Decision, request: Request):
    with _database(request) as db:
        db.execute("BEGIN IMMEDIATE")
        data = _load(db, design_id)
        accepted = A.AssemblyRevision.model_validate(data["accepted"])
        _service(request, [c.id for c in accepted.assembly.components]).validate(accepted)
        # Retrying the exact applied candidate is idempotent while it remains accepted.
        if body.action == "apply" and body.candidate_revision_id == accepted.id and accepted.parent_revision_id == body.base_revision_id:
            return _reply(data)
        if accepted.id != body.base_revision_id:
            raise TachyonError("REVISION_CONFLICT", "The accepted assembly changed; no revision was overwritten", 409)
        if body.action == "undo":
            if not data.get("previous"):
                raise TachyonError("UNDO_UNAVAILABLE", "No preceding accepted assembly is available", 409)
            data.update(accepted=data["previous"], bindings=data["previousBindings"], previous=None, previousBindings=None)
        else:
            candidate = data.get("candidate")
            if not candidate or candidate["id"] != body.candidate_revision_id:
                raise TachyonError("CANDIDATE_CONFLICT", "The requested preview is not the current candidate", 409)
            if body.action == "apply":
                revision = A.AssemblyRevision.model_validate(candidate)
                _service(request, [c.id for c in revision.assembly.components]).validate(revision)
                data.update(previous=data["accepted"], previousBindings=data["bindings"],
                            accepted=candidate, bindings=data["candidateBindings"])
        data.update(candidate=None, candidateBindings=None)
        _save(db, design_id, data)
    return _reply(data)
