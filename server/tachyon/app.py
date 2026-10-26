from contextlib import asynccontextmanager
import ipaddress
import logging
import os
import secrets
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .cad.catalog import Catalog
from .cad.inspection import source_inspection
from .cad.discovery import source_status
from .assembly_api import router as assembly_router
from .strategy_api import router as strategy_router
from .strategy_runtime import status as strategy_status
from .design_api import router as design_router
from .config import Settings
from .errors import TachyonError
from .models import WorkspacePatch
from .store import Store
from .launch import write_owner_launch, remove_owner_launch

log = logging.getLogger("uvicorn.error")


def is_lan(request):
    try:
        if not ipaddress.ip_address(request.client.host).is_loopback:
            return True
    except ValueError:
        return True
    # A local development proxy must not turn a declared phone/LAN origin into
    # loopback display permission merely because its backend connection is local.
    for host in (request.url.hostname, urlparse(request.app.state.settings.ui_origin).hostname):
        if host and host.endswith(".local"):
            return True
        try:
            if host and not ipaddress.ip_address(host).is_loopback:
                return True
        except ValueError:
            pass
    return False


def create_app(settings: Settings | None = None):
    settings = settings or Settings.environment()

    @asynccontextmanager
    async def lifespan(app):
        app.state.session = secrets.token_urlsafe(32)
        app.state.store = Store(settings.data_dir)
        write_owner_launch(settings, app.state.session)
        log.info("Tachyon is ready. Use tachyon launch with this port to open its authorized browser session.")
        try:
            yield
        finally:
            remove_owner_launch(settings, app.state.session)

    app = FastAPI(title="Tachyon", version=__version__, lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.include_router(assembly_router)
    app.include_router(strategy_router)
    app.include_router(design_router)

    @app.middleware("http")
    async def owner_session(request: Request, call_next):
        path = request.url.path
        private_headers = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}
        if path.startswith("/api/") and path != "/api/health":
            expected = getattr(app.state, "session", "")
            supplied = request.headers.get("x-tachyon-session", "")
            try:
                supplied_bytes = supplied.encode("ascii")
            except UnicodeEncodeError:
                supplied_bytes = b""
            if not expected or not secrets.compare_digest(supplied_bytes, expected.encode("ascii")):
                return JSONResponse({"code": "SESSION_REQUIRED", "message": "Open the current owner launch URL", "retryable": False}, status_code=401, headers=private_headers)
            origin = request.headers.get("origin")
            if origin and origin.rstrip("/") != settings.ui_origin:
                return JSONResponse({"code": "ORIGIN_REJECTED", "message": "This local workspace does not allow that origin", "retryable": False}, status_code=403, headers=private_headers)
        try:
            response = await call_next(request)
        except Exception:
            # Never return source paths, rights files, credentials or raw converter errors.
            log.error("A local API request failed unexpectedly")
            response = JSONResponse({"code": "INTERNAL_ERROR", "message": "The local operation failed; accepted workspace data is retained", "retryable": True}, status_code=500)
        if path.startswith("/api/"):
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(TachyonError)
    async def domain_error(request, error):
        return JSONResponse(error.public(), status_code=error.status)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": __version__, "cadProfile": "user_provided_local",
                "providerConfigured": bool(os.getenv("OPENAI_API_KEY") and os.getenv("TACHYON_AI_MODEL"))}

    @app.get("/api/catalog")
    def catalog(request: Request):
        return Catalog(settings).public(lan=is_lan(request))

    @app.get("/api/sources")
    def sources():
        # Owner-authenticated metadata only. This never converts, exposes source
        # paths/evidence, or turns discovery into a geometry-display grant.
        return source_status(settings)

    @app.get("/api/capabilities")
    def capabilities(request: Request):
        state = Catalog(settings).public(lan=is_lan(request))
        learned = strategy_status(settings.root)
        return {"canInspect": bool(state["components"]), "canGenerateStrategy": learned["available"],
                "canGenerateRobot": False, "canEdit": False,
                "reasons": [b["message"] for b in state["blockers"]] +
                           ([] if learned["available"] else [learned.get("reason", "The saved strategy runtime is unavailable")]) + [
                    "Complete authentic robot generation requires qualified components and a supported assembly recipe"]}

    @app.get("/api/assets/{mesh_hash}.glb")
    def asset(mesh_hash: str, request: Request):
        return FileResponse(Catalog(settings).asset(mesh_hash, lan=is_lan(request)), media_type="model/gltf-binary")

    @app.get("/api/inspection/{component_id}")
    def inspection(component_id: str, request: Request):
        state = Catalog(settings).public(lan=is_lan(request))
        component = next((c for c in state["components"] if c["id"] == component_id), None)
        if not component:
            raise TachyonError("COMPONENT_UNAVAILABLE", "This component is not qualified and prepared for this display context", 404)
        return source_inspection(component)

    @app.get("/api/workspace")
    def workspace():
        return app.state.store.workspace()

    @app.patch("/api/workspace")
    def patch_workspace(patch: WorkspacePatch):
        data = patch.model_dump(mode="json", by_alias=True, exclude_unset=True)
        if patch.preferences is not None:
            data["preferences"] = patch.preferences.model_dump(mode="json", exclude_none=True)
        if patch.active_component_id is not None:
            known = {c.id for c in Catalog(settings).manifest.components}
            if patch.active_component_id not in known:
                raise TachyonError("UNKNOWN_COMPONENT", "The selected component is not in this local catalog")
        if data.get("preferences") is None:
            data.pop("preferences", None)
        return app.state.store.patch_workspace(data)

    dist = settings.root / "web/dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")
    return app


app = create_app()
