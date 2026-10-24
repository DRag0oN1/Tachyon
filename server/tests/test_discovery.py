"""Metadata-only inventories, hash-bound owner assertions and redacted status."""
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import sys

import pytest

from tachyon.cad.discovery import (
    SAMPLE_BYTES, discover_sources, record_source, source_register_path, source_status,
)
from tachyon.config import MAX_SOURCE_BYTES, Settings
from tachyon.errors import TachyonError
from tachyon.models import Operation


STEP = (b"ISO-10303-21;\nHEADER;\nFILE_NAME('private-export.step','',(''),(''),'','','');\n"
        b"FILE_SCHEMA(('AP214'));\nENDSEC;\nDATA;\n#1=PRODUCT('observed-id','observed name','',());\n"
        b"#2=SI_UNIT(.MILLI.,.METRE.);\nENDSEC;\nEND-ISO-10303-21;\n")


@pytest.fixture
def inventory(tmp_path):
    settings = Settings(tmp_path / "public", tmp_path / "public/.local",
                        cad_dir=tmp_path / "external/step", rights_dir=tmp_path / "external/rights")
    settings.cad_dir.mkdir(parents=True)
    settings.rights_dir.mkdir(parents=True)
    (settings.cad_dir / "private.step").write_bytes(STEP)
    return settings


def save(path, value):
    path.write_text(json.dumps(value))


def assert_unverified(permissions, code=None):
    assert set(permissions) == {op.value for op in Operation}
    assert all(p["status"] == "unverified" for p in permissions.values())
    if code:
        assert all(p["code"] == code for p in permissions.values())


def qualify(settings, operations=("acquisition_storage", "conversion")):
    evidence = settings.rights_dir / "review.txt"
    evidence.write_text("Original synthetic metadata-test permission evidence; no manufacturer CAD.")
    permission = {"status": "qualified", "basis": "self_authored", "rightsholder": "Test author",
                  "reviewedBy": "Test reviewer", "reviewedOn": date.today().isoformat(),
                  "evidencePath": "rights:review.txt", "evidenceSha256": hashlib.sha256(evidence.read_bytes()).hexdigest()}
    save(settings.rights_dir / "rights.json", {"records": [{"sourceSha256": hashlib.sha256(STEP).hexdigest(),
        "operations": {op: dict(permission) for op in operations}}]})


def test_discovery_streams_metadata_without_native_or_network(inventory, monkeypatch):
    import builtins
    import socket

    real_import = builtins.__import__

    def no_native(name, *args, **kwargs):
        assert name.split(".")[0] not in ("cadquery", "OCP"), "Discovery imported native CAD"
        return real_import(name, *args, **kwargs)

    def no_network(*args, **kwargs):
        pytest.fail("Discovery attempted network access")

    monkeypatch.setattr(builtins, "__import__", no_native)
    monkeypatch.setattr(socket, "create_connection", no_network)
    document = discover_sources(inventory)
    assert source_register_path(inventory) == inventory.rights_dir / "source-register.json"
    source = document["sources"][0]
    assert source["sourceSha256"] == hashlib.sha256(STEP).hexdigest()
    assert source["sizeBytes"] == len(STEP) and source["sourcePath"] == "cad:private.step"
    assert source["observed"]["stepSignature"] is True
    assert source["observed"]["headerIdentities"] and source["observed"]["productIdentities"] == ["observed-id"]
    assert source["observed"]["unitDeclarations"] == [".MILLI.,.METRE."]
    assert all(value is None for value in source["provenance"].values())
    assert source["measurementState"] == "pending_reviewed_conversion"
    assert_unverified(source["permissions"])
    assert not inventory.data_dir.exists()
    assert (inventory.cad_dir / "private.step").read_bytes() == STEP
    assert not list(inventory.rights_dir.rglob("*.glb"))


def test_record_source_preserves_partial_metadata_without_granting_permissions(inventory):
    source_hash = discover_sources(inventory)["sources"][0]["sourceSha256"]
    first = record_source(inventory, source_hash, name="Recorded test component", sku="TEST-1",
                          original_url="https://example.org/original.step", provenance="Owner-supplied original",
                          terms_url="https://example.org/terms", terms="Conversion unresolved", recorded_by="Owner")
    assert_unverified(first["permissions"])
    record_source(inventory, source_hash, component_id="test_component", recorded_by="Owner")
    source = discover_sources(inventory)["sources"][0]
    assert source["provenance"]["name"] == "Recorded test component"
    assert source["provenance"]["sku"] == "TEST-1"
    assert source["provenance"]["componentId"] == "test_component"
    assert source["provenance"]["termsUrl"] == "https://example.org/terms"
    assert source["provenance"]["recordedOn"] == date.today().isoformat()
    assert_unverified(source["permissions"])


def test_changed_hash_invalidates_provenance_and_rights(inventory):
    qualify(inventory)
    first = discover_sources(inventory)["sources"][0]
    record_source(inventory, first["sourceSha256"], name="Old identity", recorded_by="Owner")
    (inventory.cad_dir / "private.step").write_bytes(STEP + b"\nchanged")
    with pytest.raises(TachyonError) as caught:
        record_source(inventory, first["sourceSha256"], name="Stale assertion", recorded_by="Owner")
    assert caught.value.code == "SOURCE_HASH_MISMATCH"
    source = discover_sources(inventory)["sources"][0]
    assert source["sourceSha256"] != first["sourceSha256"]
    assert source["provenance"]["name"] is None
    assert_unverified(source["permissions"])


def test_missing_and_restored_sources_keep_hash_bound_metadata(inventory):
    source_hash = discover_sources(inventory)["sources"][0]["sourceSha256"]
    record_source(inventory, source_hash, name="Known identity", recorded_by="Owner")
    (inventory.cad_dir / "private.step").unlink()
    source = discover_sources(inventory)["sources"][0]
    assert source["sourceState"] == "missing" and source["provenance"]["name"] == "Known identity"
    assert_unverified(source["permissions"], "LOCAL_FILE_MISSING")
    with pytest.raises(TachyonError):
        record_source(inventory, source_hash, recorded_by="Owner")
    (inventory.cad_dir / "private.step").write_bytes(STEP)
    assert discover_sources(inventory)["sources"][0]["provenance"]["name"] == "Known identity"


def test_duplicates_and_nested_extensions_have_one_status_identity(inventory):
    nested = inventory.cad_dir / "nested"
    nested.mkdir()
    (nested / "alias.STP").write_bytes(STEP)
    (nested / "ignored.f3d").write_text("ignored")
    document = discover_sources(inventory)
    assert len(document["sources"]) == 2
    source_hash = document["sources"][0]["sourceSha256"]
    record_source(inventory, source_hash, name="Shared identity", recorded_by="Owner")
    document = discover_sources(inventory)
    assert all(s["provenance"]["name"] == "Shared identity" for s in document["sources"])
    assert len(source_status(inventory)["sources"]) == 1


@pytest.mark.parametrize("body", ["null", "[]", "42", "{}", "not json", '{"schemaVersion":2}'])
def test_invalid_register_never_overwritten_or_leaked(inventory, body):
    path = source_register_path(inventory)
    path.write_text(body)
    with pytest.raises(TachyonError):
        discover_sources(inventory)
    assert path.read_text() == body
    status = source_status(inventory)
    assert status["sources"] == [] and status["blockers"][0]["code"] == "INVALID_MANIFEST"
    assert str(inventory.rights_dir) not in json.dumps(status)


def test_duplicate_paths_or_conflicting_hash_metadata_are_rejected(inventory):
    document = discover_sources(inventory)
    document["sources"].append(dict(document["sources"][0]))
    save(source_register_path(inventory), document)
    assert source_status(inventory)["blockers"][0]["code"] == "INVALID_MANIFEST"
    document["sources"][1]["sourcePath"] = "cad:other.step"
    document["sources"][1]["provenance"] = {"name": "Conflicting"}
    save(source_register_path(inventory), document)
    assert source_status(inventory)["blockers"][0]["code"] == "INVALID_MANIFEST"


def test_symlinks_cycles_and_invalid_step_are_reported_without_traversal(inventory, tmp_path):
    outside = tmp_path / "outside.step"
    outside.write_bytes(STEP)
    (inventory.cad_dir / "outside-link.step").symlink_to(outside)
    (inventory.cad_dir / "cycle").symlink_to(inventory.cad_dir, target_is_directory=True)
    (inventory.cad_dir / "bad.step").write_text("not a STEP document")
    document = discover_sources(inventory)
    assert len(document["sources"]) == 2
    assert {i["code"] for i in document["issues"]} == {"INVALID_LOCAL_PATH", "INVALID_STEP"}
    bad = next(s for s in document["sources"] if s["filename"] == "bad.step")
    assert bad["sourceState"] == "unreadable"
    assert_unverified(bad["permissions"], "INVALID_STEP")


def test_discovery_size_limit_uses_sparse_files_without_allocation(inventory):
    large = inventory.cad_dir / "too-large.step"
    with large.open("wb") as stream:
        stream.truncate(MAX_SOURCE_BYTES + 1)
    document = discover_sources(inventory)
    assert len(document["sources"]) == 1
    assert document["issues"][0]["code"] == "CAD_TOO_LARGE"


def test_observations_are_bounded_even_for_large_text(inventory):
    path = inventory.cad_dir / "private.step"
    path.write_bytes(STEP + b" " * (SAMPLE_BYTES * 2))
    source = discover_sources(inventory)["sources"][0]
    assert source["observed"]["sampleBytes"] == SAMPLE_BYTES
    assert source["observed"]["sampleTruncated"] is True
    assert source["sourceSha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_status_reads_no_unpermitted_source_bodies_and_never_mutates(inventory, monkeypatch):
    discover_sources(inventory)
    before = source_register_path(inventory).read_bytes()
    import tachyon.cad.discovery as discovery

    def forbidden(*args, **kwargs):
        pytest.fail("Read-only status hashed an unpermitted source")

    monkeypatch.setattr(discovery, "_inspect", forbidden)
    status = source_status(inventory)
    assert source_register_path(inventory).read_bytes() == before
    assert status["geometryIncluded"] is False
    assert set(status) == {"schemaVersion", "sources", "blockers", "geometryIncluded"}
    source = status["sources"][0]
    assert set(source) == {"sourceSha256", "name", "sku", "sourceUrl", "sourceState", "permissions"}
    assert source["name"] == "Unidentified STEP source"
    assert_unverified(source["permissions"])
    assert "private.step" not in json.dumps(status)
    assert str(inventory.cad_dir) not in json.dumps(status)


def test_status_rechecks_evidence_and_source_hash_before_qualification(inventory):
    qualify(inventory)
    discover_sources(inventory)
    status = source_status(inventory)["sources"][0]
    assert status["permissions"]["conversion"] == {"status": "qualified", "code": None}
    # A tampered snapshot cannot grant a different operation.
    document = json.loads(source_register_path(inventory).read_text())
    document["sources"][0]["permissions"]["public_hosting"] = {"status": "qualified", "code": None}
    save(source_register_path(inventory), document)
    assert source_status(inventory)["sources"][0]["permissions"]["public_hosting"]["status"] == "unverified"
    (inventory.rights_dir / "review.txt").write_text("Altered private evidence content")
    status = source_status(inventory)["sources"][0]
    assert status["permissions"]["conversion"]["code"] == "RIGHTS_EVIDENCE_CHANGED"
    assert "Altered private evidence" not in json.dumps(source_status(inventory))


def test_status_stat_change_immediately_blocks_qualification(inventory):
    qualify(inventory)
    discover_sources(inventory)
    (inventory.cad_dir / "private.step").write_bytes(STEP + b"changed")
    status = source_status(inventory)["sources"][0]
    assert status["sourceState"] == "changed"
    assert_unverified(status["permissions"], "SOURCE_HASH_MISMATCH")


def test_status_hashes_even_when_tampered_metadata_matches(inventory):
    qualify(inventory)
    document = discover_sources(inventory)
    source = inventory.cad_dir / "private.step"
    source.write_bytes(STEP.replace(b"observed name", b"tampered name"))
    info = source.stat()
    document["sources"][0]["stamp"] = {"sizeBytes": info.st_size, "mtimeNs": info.st_mtime_ns,
        "ctimeNs": info.st_ctime_ns, "inode": info.st_ino}
    save(source_register_path(inventory), document)
    status = source_status(inventory)["sources"][0]
    assert status["sourceState"] == "changed"
    assert_unverified(status["permissions"], "SOURCE_HASH_MISMATCH")


def test_conversion_evidence_alone_cannot_trigger_unpermitted_body_read(inventory, monkeypatch):
    import tachyon.cad.discovery as discovery

    qualify(inventory, operations=("conversion",))
    discover_sources(inventory)
    monkeypatch.setattr(discovery, "_inspect", lambda *a: pytest.fail("Unpermitted source body read"))
    assert_unverified(source_status(inventory)["sources"][0]["permissions"], "SOURCE_HASH_UNVERIFIED")


@pytest.mark.parametrize("mutation,code", [("expired", "RIGHTS_EVIDENCE_EXPIRED"),
                                           ("disallowed", "SOURCE_OPERATION_DISALLOWED"),
                                           ("missing", "LOCAL_FILE_MISSING")])
def test_status_honors_expiry_denial_and_missing_evidence(inventory, mutation, code):
    qualify(inventory)
    discover_sources(inventory)
    rights_path = inventory.rights_dir / "rights.json"
    rights = json.loads(rights_path.read_text())
    if mutation == "expired":
        rights["records"][0]["operations"]["conversion"]["expiresOn"] = (date.today() - timedelta(days=1)).isoformat()
    elif mutation == "disallowed":
        rights["records"][0]["operations"]["conversion"]["status"] = "disallowed"
    else:
        (inventory.rights_dir / "review.txt").unlink()
    save(rights_path, rights)
    assert source_status(inventory)["sources"][0]["permissions"]["conversion"]["code"] == code


@pytest.mark.parametrize("metadata", [{"permissions": {"conversion": "qualified"}},
                                      {"original_url": "file:///private/source.step"},
                                      {"terms_url": "https://owner:secret@example.org/terms"}])
def test_record_rejects_permission_fields_and_unsafe_urls_without_mutation(inventory, metadata):
    source_hash = discover_sources(inventory)["sources"][0]["sourceSha256"]
    before = source_register_path(inventory).read_bytes()
    with pytest.raises(TachyonError) as caught:
        record_source(inventory, source_hash, recorded_by="Owner", **metadata)
    assert caught.value.code == "INVALID_SOURCE_METADATA"
    assert source_register_path(inventory).read_bytes() == before


def test_cli_discover_record_status_and_explicit_missing_inputs(inventory, monkeypatch, capsys):
    from tachyon.cli import main

    monkeypatch.setattr(Settings, "environment", classmethod(lambda cls: inventory))

    def run(*args):
        monkeypatch.setattr(sys, "argv", ["tachyon", *args])
        code = main()
        return code, json.loads(capsys.readouterr().out)

    code, document = run("assets-discover")
    assert code == 0
    source_hash = document["sources"][0]["sourceSha256"]
    code, document = run("assets-record-source", "--sha256", source_hash, "--name", "Owner name",
                         "--terms-url", "https://example.org/terms", "--recorded-by", "Owner")
    assert code == 0 and document["provenance"]["name"] == "Owner name"
    assert_unverified(document["permissions"])
    code, document = run("assets-source-status")
    assert code == 2 and document["sources"][0]["name"] == "Owner name"
    code, document = run("assets-register", "--manifest", "rights:absent.json", "--rights", "rights:absent.json")
    assert code == 2 and document["code"] == "LOCAL_FILE_MISSING"


def test_settings_without_external_roots_only_use_isolated_legacy_data(tmp_path):
    settings = Settings(tmp_path, tmp_path / "data")
    sources = settings.data_dir / "sources"
    sources.mkdir(parents=True)
    (sources / "original.step").write_bytes(STEP)
    assert discover_sources(settings)["sources"][0]["sourcePath"] == "data:sources/original.step"
    assert source_register_path(settings) == settings.data_dir / "catalog/source-register.json"
    assert source_status(settings)["sources"][0]["sourceState"] == "present"
