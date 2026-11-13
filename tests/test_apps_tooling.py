"""The repository's tooling sees the Configuration Application (`apps/shell_config`): a change to its source picks its tests, CI treats its packaging file as packaging, the type ratchet checks its
source, and its tests are on the default test path. Each check fails when the tooling still looks only at `src/tess_ui` and `tests/`."""

import importlib.util
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tests_for = load("tests_for")
ci_plan = load("ci_plan")
ratchet = load("mypy_ratchet")


def test_a_change_to_the_apps_source_picks_the_apps_tests():
    tests = tests_for.load_tests()
    assert any(t.startswith("apps/shell_config/tests/test_shell_config_") for t in tests)
    picks, _ = tests_for.pick(["apps/shell_config/src/tess_shell_config/model.py"], tests)
    assert "apps/shell_config/tests/test_shell_config_model.py" in picks
    assert not any(t.startswith("apps/") and "test_shell_config_" not in t for t in picks)


def test_a_changed_apps_test_is_itself_the_pick():
    tests = tests_for.load_tests()
    picks, _ = tests_for.pick(["apps/shell_config/tests/test_shell_config_files.py"], tests)
    assert list(picks) == ["apps/shell_config/tests/test_shell_config_files.py"]


def test_the_apps_view_files_pick_a_test_that_names_them():
    tests = tests_for.load_tests()
    picks, _ = tests_for.pick(["apps/shell_config/src/tess_shell_config/Views/Main_View.yaml"], tests)
    assert any(t.startswith("apps/shell_config/tests/") for t in picks)


def test_the_apps_packaging_file_counts_as_packaging_for_ci():
    assert ci_plan.packaging_changed(["apps/shell_config/pyproject.toml"], "HEAD", "HEAD")


def test_the_type_ratchet_checks_the_apps_source():
    assert "apps/shell_config/src/tess_shell_config" in ratchet.TARGETS and "src/tess_ui" in ratchet.TARGETS


def test_the_default_test_run_includes_the_apps_tests_and_its_source():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["pytest"]["ini_options"]
    assert "apps/shell_config/tests" in config["testpaths"] and "apps/shell_config/src" in config["pythonpath"]


def test_the_apps_conftest_applies_the_real_session_guard():
    text = (ROOT / "apps" / "shell_config" / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert "real_session.ensure()" in text
