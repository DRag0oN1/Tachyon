"""Native CAD fixtures live only in pytest's private temporary directories."""
import os
import shutil
import sys
import tempfile
from pathlib import Path

# The checklist command works before an editable install as well.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(tempfile.gettempdir()) / "tachyon-test-cache"))

import pytest

from fixture_support import FixtureWorkspace, create_calibration_workspace
from tachyon.cad.prepare import prepare_component
from tachyon.config import Settings


@pytest.fixture(scope="session")
def calibration_template(tmp_path_factory):
    root = tmp_path_factory.mktemp("tachyon-original-calibration")
    return create_calibration_workspace(root, root / "data")


def copy_workspace(source, root):
    destination = root / "data"
    shutil.copytree(source.data_dir, destination)
    return FixtureWorkspace(Settings(root=root, data_dir=destination))


@pytest.fixture
def calibration_workspace(calibration_template, tmp_path):
    return copy_workspace(calibration_template, tmp_path)


@pytest.fixture(scope="session")
def prepared_template(calibration_template, tmp_path_factory):
    workspace = copy_workspace(calibration_template, tmp_path_factory.mktemp("tachyon-native-glb"))
    catalog = workspace.catalog()
    assert catalog.register()[0]["status"] == "registered"
    prepare_component(catalog, workspace.component)
    return workspace


@pytest.fixture
def prepared_workspace(prepared_template, tmp_path):
    return copy_workspace(prepared_template, tmp_path)
