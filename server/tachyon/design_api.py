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


def _service(request):
    # Resolve LAN from the app's established display/owner context. Local proxy
    # connections must never bypass the catalog's separate LAN permission gate.
    from .app import is_lan
    return RealizationService(request.app.state.settings, request.app.state.store, lan=is_lan(request))


@router.post("/realize")
def realize(body: Realize, request: Request):
    return _service(request).realize(body.architecture_id)


@router.get("/{design_id}")
def read(design_id: str, request: Request):
    return _service(request).read(design_id)


@router.post("/{design_id}/preview")
def preview(design_id: str, body: Preview, request: Request):
    return _service(request).preview(design_id, body.base_revision_id, body.configuration_id)


@router.post("/{design_id}/decision")
def decide(design_id: str, body: Decision, request: Request):
    return _service(request).decide(design_id, body.base_revision_id, body.action, body.candidate_revision_id)
