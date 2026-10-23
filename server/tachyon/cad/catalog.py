from __future__ import annotations

import hashlib
from importlib.metadata import version
import json
import re
from pathlib import Path

from pydantic import ValidationError

from ..config import Settings
from ..errors import TachyonError
from ..models import CatalogManifest, ComponentInput, Operation, RightsManifest, PreparedComponent
from .rights import RightsPolicy, sha256_file

LOCAL_OPERATIONS = [Operation.acquisition_storage, Operation.conversion,
                    Operation.assembly_placement, Operation.loopback_display]
REGISTER_OPERATIONS = [Operation.acquisition_storage]
PREPARE_OPERATIONS = [Operation.acquisition_storage, Operation.conversion]


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    temp.replace(path)


def read_json(path, model):
    try:
        return model.model_validate_json(path.read_text())
    except (OSError, ValueError, ValidationError):
        raise TachyonError("INVALID_MANIFEST", "The local catalog or rights manifest is missing or invalid") from None


class Catalog:
    def __init__(self, settings: Settings, manifest_path: Path | None = None,
                 rights_path: Path | None = None):
        self.settings = settings
        registration = settings.data_dir / "catalog/registration.json"
        if (manifest_path is None or rights_path is None) and registration.is_file():
            try:
                registered = json.loads(registration.read_text())
                if not isinstance(registered, dict):
                    raise ValueError()
                if manifest_path is None:
                    manifest_path = settings.local_path(registered["manifestPath"])
                if rights_path is None:
                    rights_path = settings.local_path(registered["rightsPath"])
            except (ValueError, KeyError, TypeError):
                raise TachyonError("INVALID_MANIFEST", "The local catalog registration is invalid") from None
        self.manifest_path = settings.local_path(str(manifest_path or settings.data_dir / "catalog/manifest.json"), must_exist=False)
        self.rights_path = settings.local_path(str(rights_path or settings.data_dir / "catalog/rights.json"), must_exist=False)
        self.manifest = read_json(self.manifest_path, CatalogManifest) if self.manifest_path.exists() else CatalogManifest()
        rights = read_json(self.rights_path, RightsManifest) if self.rights_path.exists() else RightsManifest()
        self.policy = RightsPolicy(settings, rights)

    def source(self, component: ComponentInput, operations=REGISTER_OPERATIONS):
        self.policy.require(component.source_sha256, operations)
        path = self.settings.local_path(component.source_path)
        if path.suffix.lower() not in (".step", ".stp"):
            raise TachyonError("UNSUPPORTED_CAD_FORMAT", "Supply STEP; native Fusion files are not supported")
        if path.stat().st_size > 100 * 1024 * 1024:
            raise TachyonError("CAD_TOO_LARGE", "This initial local importer supports files up to 100 MiB")
        with path.open("rb") as stream:
            if not stream.read(4096).lstrip().startswith(b"ISO-10303-21;"):
                raise TachyonError("INVALID_STEP", "The supplied source is not an ISO STEP document")
        if sha256_file(path) != component.source_sha256:
            raise TachyonError("SOURCE_HASH_MISMATCH", "Source bytes no longer match the registered component")
        if component.geometry_class == "verified_imported_component" and component.origin_kind == "tachyon_authored":
            raise TachyonError("INVALID_GEOMETRY_CLASS", "Newly authored fixtures cannot be classified as imported manufacturer parts")
        return path

    def fingerprint(self, component):
        implementation = hashlib.sha256()
        for name in ("prepare.py", "glb.py", "native.py"):
            implementation.update(Path(__file__).with_name(name).read_bytes())
        identity = {"component": component.json_data(), "cadquery": version("cadquery"),
                    "ocp": version("cadquery-ocp"), "converterCode": implementation.hexdigest()}
        return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()

    def receipt_path(self, component):
        return self.settings.data_dir / "catalog/prepared" / (self.fingerprint(component) + ".json")

    def register(self):
        write_json(self.settings.data_dir / "catalog/registration.json", {
            "manifestPath": str(self.manifest_path.relative_to(self.settings.data_dir)),
            "rightsPath": str(self.rights_path.relative_to(self.settings.data_dir))})
        results = []
        for component in self.manifest.components:
            try:
                self.source(component)
                results.append({"componentId": component.id, "status": "registered", "converted": False})
            except TachyonError as error:
                results.append({"componentId": component.id, "status": "blocked", **error.public()})
        write_json(self.settings.data_dir / "catalog/registration-report.json", {"results": results})
        return results

    def prepared(self, component, *, lan=False):
        display_operations = [Operation.acquisition_storage,
                              Operation.lan_display if lan else Operation.loopback_display]
        self.source(component, display_operations)
        receipt = self.receipt_path(component)
        if not receipt.is_file():
            raise TachyonError("MESH_NOT_PREPARED", "Registered STEP needs local preparation before inspection")
        try:
            data = json.loads(receipt.read_text())
            data = PreparedComponent.model_validate(data).json_data()
            mesh_hash = data["meshSha256"]
            if not re.fullmatch(r"[a-f0-9]{64}", mesh_hash):
                raise ValueError()
            mesh = self.settings.data_dir / "meshes" / (mesh_hash + ".glb")
            if not mesh.is_file() or sha256_file(mesh) != mesh_hash:
                raise TachyonError("MESH_HASH_MISMATCH", "The prepared mesh is missing or its bytes changed")
            if data["sourceSha256"] != component.source_sha256 or data["catalogFingerprint"] != self.fingerprint(component):
                raise TachyonError("STALE_MESH", "The source catalog changed; prepare the component again")
            for key in ("id", "name", "sku", "originKind", "geometryClass", "sourceUrl", "ports"):
                if data[key] != component.json_data()[key]:
                    raise TachyonError("STALE_MESH", "The mesh receipt no longer matches the registered component identity")
            data["declaredUse"] = "lan_source_inspection" if lan else "loopback_source_inspection"
            data["qualifiedOperations"] = [operation.value for operation in display_operations]
            return data
        except (ValueError, KeyError, TypeError):
            raise TachyonError("INVALID_RECEIPT", "Local preparation receipt is invalid") from None

    def public(self, *, lan=False):
        components, blockers = [], []
        for component in self.manifest.components:
            try:
                data = self.prepared(component, lan=lan)
                components.append(data)
            except TachyonError as error:
                blockers.append({"componentId": component.id, **error.public()})
        if not self.manifest.components:
            blockers.append({"code": "NO_LOCAL_CAD", "message": "Register permitted local STEP files to inspect CAD", "retryable": False})
        return {"profile": "user_provided_local", "components": components, "blockers": blockers}

    def asset(self, mesh_hash, *, lan=False):
        if not re.fullmatch(r"[a-f0-9]{64}", mesh_hash):
            raise TachyonError("ASSET_NOT_FOUND", "Local mesh not found", 404)
        for component in self.manifest.components:
            receipt = self.receipt_path(component)
            if receipt.exists():
                try:
                    candidate = json.loads(receipt.read_text())
                    if isinstance(candidate, dict) and candidate.get("meshSha256") == mesh_hash:
                        self.prepared(component, lan=lan)
                        return self.settings.data_dir / "meshes" / (mesh_hash + ".glb")
                except (ValueError, KeyError, TypeError):
                    pass
        raise TachyonError("ASSET_NOT_FOUND", "Local mesh not found", 404)
