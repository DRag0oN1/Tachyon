import argparse
import json
from pathlib import Path

from .cad.catalog import Catalog
from .config import Settings
from .errors import TachyonError


def _input_path(value):
    """CLI ordinary paths are cwd-relative; explicit role prefixes stay rooted."""
    if value is None:
        return None
    if any(value.startswith(prefix) for prefix in ("data:", "cad:", "rights:")):
        return value
    return str(Path(value).expanduser().absolute())


def main():
    p = argparse.ArgumentParser(prog="tachyon")
    sub = p.add_subparsers(dest="command", required=True)
    register = sub.add_parser("assets-register", help="Check local sources and reviewed rights; no conversion")
    register.add_argument("--manifest", required=True)
    register.add_argument("--rights", required=True)
    prepare = sub.add_parser("assets-prepare", help="Locally convert permitted STEP into private display meshes")
    prepare.add_argument("--manifest")
    prepare.add_argument("--rights")
    discover = sub.add_parser("assets-discover", help="Write a private source-register.json; metadata only, no conversion or permission grants")
    discover.add_argument("--rights", help="Reviewed rights manifest (default: rights:rights.json)")
    record = sub.add_parser("assets-record-source", help="Record owner provenance for a current discovered hash; no permission approval")
    record.add_argument("--sha256", required=True)
    record.add_argument("--original-url")
    record.add_argument("--component-id")
    record.add_argument("--name")
    record.add_argument("--sku")
    record.add_argument("--origin-kind", choices=["manufacturer_cad", "community_component_model", "tachyon_authored"])
    record.add_argument("--provenance")
    record.add_argument("--terms-url")
    record.add_argument("--terms")
    record.add_argument("--recorded-by", required=True)
    sub.add_parser("assets-source-status", help="Read redacted discovery and per-operation permission status")
    measure = sub.add_parser("assets-measure", help="Measure permitted native STEP into metadata; no meshes or permission approval")
    measure.add_argument("--source", required=True)
    measure.add_argument("--rights")
    measure.add_argument("--reference-only", action="store_true", help="Report source defects for inspection; does not qualify defective geometry for robot generation")
    serve = sub.add_parser("serve", help="Run the private local studio")
    serve.add_argument("--port", type=int, default=8019)
    serve.add_argument("--open", action="store_true", help="Open this server's authorized browser session")
    launch = sub.add_parser("launch", help="Open the running server's current authorized session")
    launch.add_argument("--port", type=int, default=8019)
    launch.add_argument("--show-url", action="store_true", help="Print the private launch URL only when needed for connection recovery")
    args = p.parse_args()
    try:
        settings = Settings.environment()
        if args.command in ("serve", "launch"):
            if not 1 <= args.port <= 65535: raise ValueError()
            from .launch import open_owner_launch
            if args.command == "launch":
                url = open_owner_launch(settings, port=args.port, show_url=args.show_url)
                print(url if url else "Authorized Tachyon session opened in your browser.")
                return 0
            import uvicorn
            from contextlib import asynccontextmanager
            from .app import create_app
            settings.ui_origin = f"http://127.0.0.1:{args.port}"
            application = create_app(settings)
            original = application.router.lifespan_context
            @asynccontextmanager
            async def lifespan(app):
                async with original(app):
                    if args.open:
                        import threading
                        threading.Thread(target=open_owner_launch_browser, args=(app,), daemon=True).start()
                    yield
            def open_owner_launch_browser(app):
                # Startup is not yet accepting requests; the private token is
                # supplied directly to the OS browser, never returned over HTTP.
                import time
                for _ in range(50):
                    try:
                        open_owner_launch(settings, port=args.port)
                        return
                    except TachyonError as error:
                        if error.code == 'BROWSER_UNAVAILABLE': break
                        time.sleep(.1)
                print("Use tachyon launch after the server is ready to open its authorized session.")
            application.router.lifespan_context = lifespan
            uvicorn.run(application, host="127.0.0.1", port=args.port)
            return 0
        if args.command in ("assets-discover", "assets-record-source", "assets-source-status"):
            from .cad.discovery import discover_sources, record_source, source_status
            if args.command == "assets-discover":
                document = discover_sources(settings, _input_path(args.rights))
            elif args.command == "assets-record-source":
                fields = ("original_url", "component_id", "name", "sku", "origin_kind", "provenance", "terms_url", "terms", "recorded_by")
                document = record_source(settings, args.sha256, **{field: getattr(args, field) for field in fields})
            else:
                document = source_status(settings)
            print(json.dumps(document, indent=2))
            return 2 if document.get("issues") or document.get("blockers") else 0
        if args.command == "assets-measure":
            from .cad.qualification import measure_source
            document = measure_source(settings, _input_path(args.source), _input_path(args.rights), args.reference_only)
            print(json.dumps(document, indent=2))
            return 0
        manifest = _input_path(args.manifest)
        rights = _input_path(args.rights)
        catalog = Catalog(settings, manifest, rights)
        if args.command == "assets-register":
            result = catalog.register()
        else:
            from .cad.prepare import prepare_component
            result = []
            for component in catalog.manifest.components:
                try:
                    record = prepare_component(catalog, component)
                    result.append({"componentId": component.id, "status": "prepared", "meshSha256": record["meshSha256"]})
                except TachyonError as error:
                    result.append({"componentId": component.id, "status": "blocked", **error.public()})
        print(json.dumps({"results": result}, indent=2))
        return 2 if any(r["status"] == "blocked" for r in result) else 0
    except TachyonError as error:
        print(json.dumps(error.public()))
        return 2
    except (OSError, ValueError):
        print(json.dumps(TachyonError("INVALID_LOCAL_CONFIGURATION", "Local configuration or input could not be read; check configured private roots and files").public()))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
