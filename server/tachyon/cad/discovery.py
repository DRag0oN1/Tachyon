"""Private source inventory, owner assertions, and a redacted read-only status.

Hashing is streamed; observations use at most 64 KiB of STEP text. This module
never imports a native CAD reader, generates geometry, downloads, or grants rights.
The source register is deliberately separate from the measured CatalogManifest.
"""
from __future__ import annotations

from datetime import date
import hashlib
import os
from pathlib import Path
import re
import stat
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator

from ..config import MAX_SOURCE_BYTES, Settings
from ..errors import TachyonError
from ..models import Model, Operation, RightsManifest
from .catalog import read_json, write_json
from .rights import RightsPolicy

SAMPLE_BYTES = 64 * 1024


class SourceProvenance(Model):
    original_url: str | None = None
    component_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,100}$")
    name: str | None = None
    sku: str | None = None
    origin_kind: Literal["manufacturer_cad", "community_component_model", "tachyon_authored"] | None = None
    provenance: str | None = None
    terms_url: str | None = None
    terms: str | None = None
    recorded_by: str | None = None
    recorded_on: date | None = None

    @model_validator(mode="after")
    def valid_urls(self):
        for value in (self.original_url, self.terms_url):
            if value is not None:
                parsed = urlsplit(value)
                if (parsed.scheme not in ("http", "https") or not parsed.hostname
                        or parsed.username or parsed.password or any(c.isspace() for c in value)):
                    raise ValueError("Source and terms URLs must be HTTP(S) without credentials")
        return self


class SourceStamp(Model):
    size_bytes: int = Field(ge=0, le=MAX_SOURCE_BYTES)
    mtime_ns: int
    ctime_ns: int
    inode: int


class Observations(Model):
    step_signature: bool
    header_identities: list[str] = Field(default_factory=list)
    product_identities: list[str] = Field(default_factory=list)
    unit_declarations: list[str] = Field(default_factory=list)
    sample_bytes: int = Field(ge=0, le=SAMPLE_BYTES)
    sample_truncated: bool


class PermissionState(Model):
    status: Literal["qualified", "unverified", "disallowed"] = "unverified"
    code: str | None = "SOURCE_NOT_QUALIFIED"


class DiscoveredSource(Model):
    source_path: str
    filename: str
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    size_bytes: int = Field(ge=0, le=MAX_SOURCE_BYTES)
    source_state: Literal["present", "missing", "changed", "unreadable"]
    stamp: SourceStamp
    observed: Observations
    provenance: SourceProvenance = Field(default_factory=SourceProvenance)
    permissions: dict[Operation, PermissionState] = Field(default_factory=dict)
    measurement_state: Literal["pending_reviewed_conversion"] = "pending_reviewed_conversion"


class DiscoveryIssue(Model):
    source_path: str
    code: str
    message: str


class SourceRegister(Model):
    schema_version: Literal[1] = 1
    source_root: str
    rights_path: str
    sources: list[DiscoveredSource] = Field(default_factory=list)
    issues: list[DiscoveryIssue] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_paths(self):
        if len({s.source_path for s in self.sources}) != len(self.sources):
            raise ValueError("Duplicate discovered path")
        identities = {}
        for source in self.sources:
            identity = source.provenance.json_data()
            if source.source_sha256 in identities and identities[source.source_sha256] != identity:
                raise ValueError("Conflicting provenance for duplicate bytes")
            identities[source.source_sha256] = identity
        return self


def source_register_path(settings: Settings) -> Path:
    return settings.rights_path("rights:source-register.json" if settings.rights_dir else
                                "catalog/source-register.json", must_exist=False)


def default_rights_path(settings: Settings) -> Path:
    return settings.rights_path("rights:rights.json" if settings.rights_dir else
                                "catalog/rights.json", must_exist=False)


def _source_root(settings):
    root = settings.cad_dir or settings.data_dir / "sources"
    # Resolve again to reject a root replaced with a symlink after configuration.
    return settings.source_path(str(root), must_exist=False)


def _read_register(settings):
    path = source_register_path(settings)
    if not path.exists():
        return None
    register = read_json(path, SourceRegister)
    if register.source_root != str(_source_root(settings)):
        raise TachyonError("SOURCE_ROOT_CHANGED", "The source root changed; run assets-discover with the intended roots")
    settings.rights_path(register.rights_path, must_exist=False)
    return register


def _policy(settings, path):
    path = settings.rights_path(str(path), must_exist=False)
    return RightsPolicy(settings, read_json(path, RightsManifest) if path.exists() else RightsManifest())


def _unverified(code="SOURCE_NOT_QUALIFIED"):
    return {op.value: {"status": "unverified", "code": code} for op in Operation}


def _stamp(info):
    return SourceStamp(size_bytes=info.st_size, mtime_ns=info.st_mtime_ns,
                       ctime_ns=info.st_ctime_ns, inode=info.st_ino)


def _observe(sample, size):
    text = sample.decode("latin-1")
    # These are literal observations, never verified component identity or units.
    def declarations(pattern):
        return list(dict.fromkeys(re.findall(pattern, text, re.I | re.S)))[:16]

    return Observations(
        step_signature=sample.lstrip().startswith(b"ISO-10303-21;"),
        header_identities=declarations(r"(?:FILE_NAME|FILE_DESCRIPTION|FILE_SCHEMA)\s*\((.{0,1024}?)\)\s*;"),
        product_identities=declarations(r"\bPRODUCT\s*\(\s*'((?:[^']|''){0,200})'"),
        unit_declarations=declarations(r"\b(?:SI_UNIT|CONVERSION_BASED_UNIT)\s*\(([^)]{0,200})\)"),
        sample_bytes=len(sample), sample_truncated=size > len(sample))


def _inspect(path):
    # Nonblocking open also prevents a swapped FIFO from hanging the CLI.
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise TachyonError("INVALID_LOCAL_PATH", "A source must be a regular file")
        if before.st_size > MAX_SOURCE_BYTES:
            raise TachyonError("CAD_TOO_LARGE", "Source discovery supports files up to 256 MiB")
        digest = hashlib.sha256()
        sample = b""
        total = 0
        while chunk := stream.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_SOURCE_BYTES:
                raise TachyonError("CAD_TOO_LARGE", "Source discovery supports files up to 256 MiB")
            digest.update(chunk)
            if len(sample) < SAMPLE_BYTES:
                sample += chunk[:SAMPLE_BYTES - len(sample)]
        after = os.fstat(stream.fileno())
    if _stamp(before) != _stamp(after) or _stamp(after) != _stamp(path.stat()) or total != before.st_size:
        raise TachyonError("SOURCE_CHANGED_DURING_DISCOVERY", "Source changed while hashing; run assets-discover again")
    return digest.hexdigest(), _stamp(after), _observe(sample, total)


def discover_sources(settings: Settings, rights_path: str | None = None):
    """Explicit CLI write: inventory STEP metadata, preserving only identical hashes."""
    register = _read_register(settings)
    root = _source_root(settings)
    if not root.is_dir():
        raise TachyonError("SOURCE_DIRECTORY_MISSING", "Create the configured source directory and copy supplied STEP files into it")
    rights = settings.rights_path(str(rights_path or (register.rights_path if register else
                                                    default_rights_path(settings))), must_exist=rights_path is not None)
    policy = _policy(settings, rights)
    old = {source.source_path: source for source in register.sources} if register else {}
    identities = {s.source_sha256: s.provenance for s in old.values()}
    sources, issues, seen = [], [], set()

    def issue(path, code, message):
        issues.append(DiscoveryIssue(source_path=str(path), code=code, message=message))

    def walk_error(error):
        raise TachyonError("SOURCE_DIRECTORY_UNREADABLE", "A source directory could not be scanned; no register was changed") from None

    for directory, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
        # Do not follow directory symlinks, including cycles and links to other roots.
        for name in sorted(dirs[:]):
            path = Path(directory) / name
            if path.is_symlink():
                dirs.remove(name)
                issue(path, "INVALID_LOCAL_PATH", "Discovery does not follow symbolic links")
        dirs.sort()
        for name in sorted(files):
            path = Path(directory) / name
            if path.suffix.lower() not in (".step", ".stp"):
                continue
            reference = ("cad:" + path.relative_to(root).as_posix()) if settings.cad_dir else (
                "data:" + path.relative_to(settings.data_dir).as_posix())
            seen.add(reference)
            try:
                if path.is_symlink():
                    raise TachyonError("INVALID_LOCAL_PATH", "Discovery does not follow symbolic links")
                path = settings.source_path(str(path))
                source_hash, stamp, observed = _inspect(path)
                state = "present" if observed.step_signature else "unreadable"
                if not observed.step_signature:
                    issue(reference, "INVALID_STEP", "Source lacks an ISO STEP signature; no geometry was read")
                sources.append(DiscoveredSource(
                    source_path=reference, filename=name, source_sha256=source_hash,
                    size_bytes=stamp.size_bytes, source_state=state, stamp=stamp, observed=observed,
                    provenance=identities.get(source_hash, SourceProvenance()),
                    permissions=policy.operation_status(source_hash) if state == "present" else _unverified("INVALID_STEP")))
            except (OSError, TachyonError) as error:
                code = error.code if isinstance(error, TachyonError) else "SOURCE_UNREADABLE"
                issue(reference, code, "Source could not be safely inventoried; fix it and run assets-discover again")
                if reference in old:
                    source = old[reference].model_copy(deep=True)
                    source.source_state = "unreadable"
                    source.permissions = {Operation(op): PermissionState.model_validate(value) for op, value in _unverified(code).items()}
                    sources.append(source)
    for reference, source in old.items():
        if reference not in seen:
            source = source.model_copy(deep=True)
            source.source_state = "missing"
            source.permissions = {Operation(op): PermissionState.model_validate(value) for op, value in _unverified("LOCAL_FILE_MISSING").items()}
            sources.append(source)
    document = SourceRegister(source_root=str(root), rights_path=str(rights),
                              sources=sorted(sources, key=lambda s: s.source_path), issues=issues)
    write_json(source_register_path(settings), document.json_data())
    return document.json_data()


def record_source(settings: Settings, source_hash: str, **metadata):
    """Record owner assertions for current bytes. No permission inputs are accepted."""
    if not re.fullmatch(r"[a-f0-9]{64}", source_hash):
        raise TachyonError("INVALID_SOURCE_HASH", "Supply the discovered SHA-256")
    register = _read_register(settings)
    matches = [s for s in register.sources if s.source_sha256 == source_hash] if register else []
    if not matches:
        raise TachyonError("SOURCE_NOT_DISCOVERED", "Run assets-discover and use a current discovered SHA-256")
    current = [s for s in matches if s.source_state == "present"]
    if not current:
        raise TachyonError("SOURCE_NOT_CURRENT", "Restore a valid source and run assets-discover before recording provenance")
    updates = {}
    try:
        for source in current:
            path = settings.source_path(source.source_path)
            observed_hash, stamp, _ = _inspect(path)
            if observed_hash != source_hash:
                raise TachyonError("SOURCE_HASH_MISMATCH", "Source bytes changed; run assets-discover before recording provenance")
            updates[source.source_path] = stamp
        # Partial updates preserve other owner metadata for the same exact bytes.
        values = matches[0].provenance.model_dump()
        values.update({key: value.strip() if isinstance(value, str) else value
                       for key, value in metadata.items() if value is not None})
        if not values.get("recorded_by"):
            raise TachyonError("SOURCE_RECORDER_REQUIRED", "Supply --recorded-by to identify the owner recording these facts")
        values["recorded_on"] = date.today()
        provenance = SourceProvenance.model_validate(values)
    except ValueError:
        raise TachyonError("INVALID_SOURCE_METADATA", "Source metadata is invalid; use known HTTP(S) URLs and no permission fields") from None
    except OSError:
        raise TachyonError("SOURCE_UNREADABLE", "Source could not be verified; run assets-discover again") from None
    policy = _policy(settings, register.rights_path)
    for source in matches:
        source.provenance = provenance
        if source.source_path in updates:
            source.stamp = updates[source.source_path]
            source.permissions = {Operation(op): PermissionState.model_validate(value) for op, value in policy.operation_status(source_hash).items()}
    write_json(source_register_path(settings), register.json_data())
    return {"sourceSha256": source_hash, "provenance": provenance.json_data(),
            "permissions": policy.operation_status(source_hash), "measurementState": "pending_reviewed_conversion"}


def _current_state(settings, source):
    if source.source_state != "present":
        return source.source_state
    try:
        path = settings.source_path(source.source_path)
        info = path.stat()
        return "present" if stat.S_ISREG(info.st_mode) and _stamp(info) == source.stamp else "changed"
    except TachyonError as error:
        return "missing" if error.code == "LOCAL_FILE_MISSING" else "unreadable"
    except (OSError, ValueError):
        return "unreadable"


def source_status(settings: Settings):
    """Read-only UI contract. No filenames, paths, evidence text or full provenance.

    A stat mismatch blocks immediately. A qualified storage record permits a
    streamed source hash recheck before any qualified status is returned. Without
    storage permission this method reads only the register, stats and rights
    evidence; the explicit discovery CLI remains the hash inventory operation.
    """
    result = {"schemaVersion": 1, "sources": [], "blockers": [], "geometryIncluded": False}
    try:
        register = _read_register(settings)
        if register is None or not register.sources:
            result["blockers"].append({"code": "NO_DISCOVERED_SOURCES", "message": "Copy supplied STEP into the configured source root and run assets-discover"})
            return result
        try:
            policy = _policy(settings, register.rights_path)
            policy_error = None
        except TachyonError as error:
            policy, policy_error = None, error.code
        grouped = {}
        for source in register.sources:
            grouped.setdefault(source.source_sha256, []).append(source)
        for source_hash, copies in grouped.items():
            states = [(s, _current_state(settings, s)) for s in copies]
            source, state = next(((s, state) for s, state in states if state == "present"), states[0])
            permissions = policy.operation_status(source_hash) if policy else _unverified(policy_error)
            code = {"missing": "LOCAL_FILE_MISSING", "changed": "SOURCE_HASH_MISMATCH", "unreadable": "SOURCE_UNREADABLE"}.get(state)
            if state == "present" and any(p["status"] == "qualified" for p in permissions.values()):
                if permissions[Operation.acquisition_storage.value]["status"] != "qualified":
                    code = "SOURCE_HASH_UNVERIFIED"
                else:
                    try:
                        path = settings.source_path(source.source_path)
                        current_hash, _, _ = _inspect(path)
                        if current_hash != source_hash:
                            state, code = "changed", "SOURCE_HASH_MISMATCH"
                    except (OSError, TachyonError):
                        state, code = "unreadable", "SOURCE_UNREADABLE"
            if code:
                permissions = _unverified(code)
            result["sources"].append({
                "sourceSha256": source_hash, "name": source.provenance.name or "Unidentified STEP source",
                "sku": source.provenance.sku, "sourceUrl": source.provenance.original_url,
                "sourceState": state, "permissions": permissions})
        if register.issues:
            result["blockers"].append({"code": "SOURCE_DISCOVERY_ISSUES", "message": "Inspect the private assets-discover report and resolve skipped or invalid inputs"})
        if any(s["sourceState"] != "present" for s in result["sources"]):
            result["blockers"].append({"code": "SOURCE_NOT_CURRENT", "message": "Restore sources or run assets-discover to refresh changed files"})
        if any(p["status"] == "unverified" for s in result["sources"] for p in s["permissions"].values()):
            result["blockers"].append({"code": "SOURCE_REVIEW_REQUIRED", "message": "Record known provenance and provide reviewed evidence for each intended operation"})
    except TachyonError as error:
        result["blockers"].append({"code": error.code, "message": "Source metadata is unavailable; inspect the private register and run assets-discover"})
    return result
