import argparse
import json
from pathlib import Path

from .cad.catalog import Catalog
from .config import Settings
from .errors import TachyonError


def main():
    p = argparse.ArgumentParser(prog="tachyon")
    sub = p.add_subparsers(dest="command", required=True)
    register = sub.add_parser("assets-register", help="Check local sources and reviewed rights; no conversion")
    register.add_argument("--manifest", required=True, type=Path)
    register.add_argument("--rights", required=True, type=Path)
    prepare = sub.add_parser("assets-prepare", help="Locally convert permitted STEP into private display meshes")
    prepare.add_argument("--manifest", type=Path)
    prepare.add_argument("--rights", type=Path)
    args = p.parse_args()
    try:
        settings = Settings.environment()
        manifest = args.manifest.resolve() if args.manifest else None
        rights = getattr(args, "rights", None)
        rights = rights.resolve() if rights else None
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


if __name__ == "__main__":
    raise SystemExit(main())
