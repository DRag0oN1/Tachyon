"""External inputs have separate roles; every cache stays in private data."""
from dataclasses import replace
from pathlib import Path

import pytest

from fixture_support import digest, load_json, save_json
from tachyon.cad.catalog import Catalog
from tachyon.cad.prepare import prepare_component
from tachyon.config import MAX_SOURCE_BYTES, Settings
from tachyon.errors import TachyonError


@pytest.fixture
def external_settings(tmp_path):
    root = tmp_path / "project"
    settings = Settings(root, root / ".local", cad_dir=tmp_path / "external/step",
                        rights_dir=tmp_path / "external/rights")
    for directory in (settings.data_dir, settings.cad_dir, settings.rights_dir):
        directory.mkdir(parents=True)
    return settings


def test_optional_roots_preserve_positional_settings_and_never_default_to_user_paths(tmp_path):
    settings = Settings(tmp_path, tmp_path / "data", "http://localhost:8000")
    assert settings.cad_dir is None and settings.rights_dir is None
    assert settings.local_path("test.json", must_exist=False) == tmp_path / "data/test.json"


def test_environment_defaults_and_explicit_roots_are_isolated(tmp_path, monkeypatch):
    import tachyon.config as config

    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path / "project")
    expanduser = Path.expanduser

    def isolated_expanduser(path):
        return tmp_path / "home" / str(path)[2:] if str(path).startswith("~/") else expanduser(path)

    monkeypatch.setattr(Path, "expanduser", isolated_expanduser)
    for variable in ("TACHYON_DATA_DIR", "TACHYON_CAD_DIR", "TACHYON_RIGHTS_DIR", "TACHYON_CAD_PROFILE", "TACHYON_UI_ORIGIN"):
        monkeypatch.delenv(variable, raising=False)
    settings = Settings.environment()
    assert settings.cad_dir == tmp_path / "home/Documents/TachyonCAD/step"
    assert settings.rights_dir == tmp_path / "home/Documents/TachyonCAD/rights"
    monkeypatch.setenv("TACHYON_CAD_DIR", str(tmp_path / "other-step"))
    monkeypatch.setenv("TACHYON_RIGHTS_DIR", str(tmp_path / "other-rights"))
    assert Settings.environment().cad_dir == tmp_path / "other-step"
    assert Settings.environment().rights_dir == tmp_path / "other-rights"


@pytest.mark.parametrize("role", ["cad_dir", "rights_dir"])
def test_external_root_cannot_be_public_project_or_its_ancestor(external_settings, role):
    settings = external_settings
    for path in (settings.root, settings.root / "public", settings.root.parent):
        with pytest.raises(ValueError):
            replace(settings, **{role: path})
    # The legacy private data root remains a valid explicit configuration.
    assert getattr(replace(settings, **{role: settings.data_dir / "inputs"}), role).is_relative_to(settings.data_dir)


def test_external_root_symlink_into_public_project_is_rejected(external_settings):
    settings = external_settings
    link = settings.root.parent / "public-link"
    link.symlink_to(settings.root, target_is_directory=True)
    with pytest.raises(ValueError):
        replace(settings, cad_dir=link)


@pytest.mark.parametrize("prefix,method,root_field", [
    ("cad", "source_path", "cad_dir"), ("rights", "rights_path", "rights_dir"),
    ("data", "local_path", "data_dir"),
])
def test_role_paths_absolute_prefixed_and_legacy_paths(external_settings, prefix, method, root_field):
    settings = external_settings
    path = getattr(settings, root_field) / "sample.txt"
    path.write_text("metadata")
    resolver = getattr(settings, method)
    assert resolver(str(path)) == path
    assert resolver(f"{prefix}:sample.txt") == path
    private = settings.data_dir / "private.txt"
    private.write_text("private metadata")
    assert resolver("private.txt") == private
    assert resolver("data:private.txt") == private


@pytest.mark.parametrize("method,prefix", [("local_path", "cad"), ("local_path", "rights"),
                                          ("source_path", "rights"), ("rights_path", "cad")])
def test_roles_cannot_read_other_external_roots(external_settings, method, prefix):
    settings = external_settings
    path = getattr(settings, prefix + "_dir") / "forbidden.txt"
    path.write_text("other role")
    for value in (str(path), f"{prefix}:forbidden.txt"):
        with pytest.raises(TachyonError, match="configured private root"):
            getattr(settings, method)(value)


@pytest.mark.parametrize("method,prefix,root_field", [("source_path", "cad", "cad_dir"),
                                                    ("rights_path", "rights", "rights_dir"),
                                                    ("local_path", "data", "data_dir")])
def test_traversal_and_file_and_directory_symlink_escapes(external_settings, method, prefix, root_field):
    settings = external_settings
    root = getattr(settings, root_field)
    outside = settings.root.parent / "not-allowed.txt"
    outside.write_text("outside")
    (root / "file-link").symlink_to(outside)
    (root / "dir-link").symlink_to(outside.parent, target_is_directory=True)
    for suffix in ("../not-allowed.txt", "file-link", "dir-link/not-allowed.txt", "/not-allowed.txt"):
        with pytest.raises(TachyonError) as caught:
            getattr(settings, method)(f"{prefix}:{suffix}", must_exist=False)
        assert caught.value.code == "INVALID_LOCAL_PATH"


def test_external_symlink_cannot_jump_into_another_allowed_root(external_settings):
    settings = external_settings
    source = settings.data_dir / "private.step"
    source.write_text("ISO-10303-21;")
    (settings.cad_dir / "jump.step").symlink_to(source)
    with pytest.raises(TachyonError):
        settings.source_path("cad:jump.step")


def test_replaced_configured_root_cannot_escape(external_settings):
    settings = external_settings
    outside = settings.root.parent / "unconfigured"
    outside.mkdir()
    (outside / "source.step").write_text("ISO-10303-21;")
    settings.cad_dir.rmdir()
    settings.cad_dir.symlink_to(outside, target_is_directory=True)
    with pytest.raises(TachyonError):
        settings.source_path("cad:source.step")


@pytest.mark.parametrize("keyword", ["manifest_path", "rights_path"])
def test_explicit_missing_catalog_inputs_fail_but_absent_defaults_are_empty(external_settings, keyword):
    settings = external_settings
    assert Catalog(settings).manifest.components == []
    with pytest.raises(TachyonError) as caught:
        Catalog(settings, **{keyword: "rights:missing.json"})
    assert caught.value.code == "LOCAL_FILE_MISSING"


def test_external_manifests_evidence_and_original_prepare_only_private_cache(calibration_workspace, tmp_path):
    workspace = calibration_workspace
    external = tmp_path.parent / (tmp_path.name + "-external")
    settings = replace(workspace.settings, cad_dir=external / "step", rights_dir=external / "rights")
    settings.cad_dir.mkdir(parents=True)
    settings.rights_dir.mkdir(parents=True)
    source = settings.cad_dir / "calibration.step"
    source.write_bytes(workspace.source_path.read_bytes())
    evidence = settings.rights_dir / "authorship.txt"
    evidence.write_bytes(workspace.evidence_path.read_bytes())
    manifest = load_json(workspace.manifest_path)
    manifest["components"][0]["sourcePath"] = "cad:calibration.step"
    rights = load_json(workspace.rights_path)
    for permission in rights["records"][0]["operations"].values():
        permission["evidencePath"] = "rights:authorship.txt"
    save_json(settings.rights_dir / "manifest.json", manifest)
    save_json(settings.rights_dir / "rights.json", rights)
    catalog = Catalog(settings, "rights:manifest.json", "rights:rights.json")
    assert catalog.register()[0]["status"] == "registered"
    assert load_json(settings.data_dir / "catalog/registration.json") == {
        "manifestPath": str(settings.rights_dir / "manifest.json"), "rightsPath": str(settings.rights_dir / "rights.json")}
    restored = Catalog(settings)
    assert restored.manifest_path == settings.rights_dir / "manifest.json"
    receipt = prepare_component(restored, restored.manifest.components[0])
    assert receipt["sourceSha256"] == digest(source)
    assert restored.asset(receipt["meshSha256"]).is_relative_to(settings.data_dir)
    assert not list(settings.cad_dir.rglob("*.glb"))
    assert not list(settings.rights_dir.rglob("*.glb"))


@pytest.mark.parametrize("reported_size,allowed", [(119373056, True), (MAX_SOURCE_BYTES, True), (MAX_SOURCE_BYTES + 1, False)])
def test_bounded_catalog_cap_without_allocating_large_sources(calibration_workspace, monkeypatch, reported_size, allowed):
    # Report only the source's stat size. Actual original fixture bytes/hash stay intact.
    import os

    workspace = calibration_workspace
    original_stat = Path.stat

    def source_stat(path, *args, **kwargs):
        info = original_stat(path, *args, **kwargs)
        if path == workspace.source_path:
            values = list(info)
            values[6] = reported_size
            return os.stat_result(values)
        return info

    monkeypatch.setattr(Path, "stat", source_stat)
    if allowed:
        assert workspace.catalog().source(workspace.component) == workspace.source_path
    else:
        with pytest.raises(TachyonError) as caught:
            workspace.catalog().source(workspace.component)
        assert caught.value.code == "CAD_TOO_LARGE"
