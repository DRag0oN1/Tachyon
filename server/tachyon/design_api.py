"""Owner-authenticated design router; main owns app inclusion and rendering.

Wire with app.include_router(router) before the static mount. The hosting app
must supply app.state.settings, app.state.store and its existing owner-session
middleware. Browser rendering uses accepted/candidate assembly.instances, the
corresponding flat worldTransforms map, exact-revision bindings, and components
(full prepared public receipts). Missing qualification returns 200/blocked with
no geometry; invalid commands and stale revision pointers are explicit errors.
"""
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field

from .models import Model
from .realization import RealizationService

router = APIRouter(prefix="/api/designs")


class Realize(Model):
    architecture_id: str = Field(min_length=1, max_length=200)


class Preview(Model):
    base_revision_id: str = Field(min_length=1, max_length=100)
    configuration_id: Literal["lower", "raised"]


class Decision(Model):
    base_revision_id: str = Field(min_length=1, max_length=100)
    candidate_revision_id: str | None = Field(default=None, min_length=1, max_length=100)
    action: Literal["apply", "discard", "undo"]


class OperationPreview(Model):
    base_revision_id: str = Field(min_length=1,max_length=100)


def _service(request):
    # Resolve LAN from the app's established display/owner context. Local proxy
    # connections must never bypass the catalog's separate LAN permission gate.
    from .app import is_lan
    return RealizationService(request.app.state.settings, request.app.state.store, lan=is_lan(request))


@router.post("/realize")
def realize(body: Realize, request: Request):
    return _service(request).realize(body.architecture_id)


@router.get("/catalog")
def catalog(request: Request):
    """Discovery metadata only; opening a design rechecks its current inputs."""
    return _service(request).design_catalog()


@router.get("/{design_id}")
def read(design_id: str, request: Request):
    return _service(request).read(design_id)


@router.post("/{design_id}/preview")
def preview(design_id: str, body: Preview, request: Request):
    return _service(request).preview(design_id, body.base_revision_id, body.configuration_id)


@router.post("/{design_id}/decision")
def decide(design_id: str, body: Decision, request: Request):
    return _service(request).decide(design_id, body.base_revision_id, body.action, body.candidate_revision_id)


@router.post("/{design_id}/operation")
def operation(design_id: str, body: OperationPreview, request: Request):
    """Transient kinematic presentation; never edits the accepted design."""
    from . import assemblies as A,realization as R
    from .cad.catalog import Catalog
    from .errors import TachyonError
    from .models import Operation
    from .operation import build_operation,OBJECT_IDS
    service=_service(request)
    with service._database() as db:
        data=service._load(db,design_id)
    if data.get('candidate'):
        raise TachyonError('OPERATION_PREVIEW_CONFLICT','Apply or discard the pending design revision before playing an operation',409)
    if not data.get('accepted') or data['accepted']['id']!=body.base_revision_id:
        raise TachyonError('REVISION_CONFLICT','The operation must identify the current accepted assembly revision',409)
    context,recipe=service._context(data)
    try:
        assembly,public=service._current(data,context,recipe)
    except R.QualificationBlocked:
        raise TachyonError('OPERATION_UNAVAILABLE','Current geometry or local assembly rights are unavailable',409) from None
    facts_path=service.settings.local_path('generation-facts.json',must_exist=False)
    if not facts_path.is_file():
        raise TachyonError('OPERATION_UNSUPPORTED','This design has no verified modeled operation recipe',409)
    try:
        facts=R._bounded_json(facts_path.read_bytes())
    except (OSError,ValueError):
        raise TachyonError('OPERATION_UNSUPPORTED','The modeled operation facts are unavailable or invalid',409) from None
    catalog=Catalog(service.settings)
    for identity in OBJECT_IDS:
        component=next((c for c in catalog.manifest.components if c.id==identity),None)
        if component is None:
            raise TachyonError('OPERATION_OBJECT_MISSING','A required authored game-object or target fixture is missing',409)
        catalog.source(component,[Operation.assembly_placement])
        public.append(catalog.prepared(component,lan=service.lan))
    return build_operation(assembly,context,recipe,A.AssemblyRevision.model_validate(data['accepted']),public,facts)
