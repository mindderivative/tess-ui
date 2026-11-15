"""A bare local test run keeps the person's own session out of reach (tests/real_session.py, applied by tests/conftest.py and apps/shell_config/tests/conftest.py)."""

import real_session
from real_session import REAL_SESSION_VARIABLES, keep_off_the_real_session, software_vulkan_icd

REAL = {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-1", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus", "XDG_RUNTIME_DIR": "/run/user/1000", "XDG_CONFIG_HOME": "/home/x/.config", "OTHER": "kept"}


def test_the_real_session_is_dropped_and_the_user_folders_move():
    env = dict(REAL)
    removed = keep_off_the_real_session(env)
    assert set(removed) == {"DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS"}
    assert not any(name in env for name in REAL_SESSION_VARIABLES)
    assert env["OTHER"] == "kept"
    for name in ("XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "XDG_CACHE_HOME"):
        assert "tess-ui-tests-" in env[name]
    assert "tess-ui-tests-" in env["TESS_UI_STATE_DIR"]


def test_an_explicit_allow_keeps_the_session():
    env = dict(REAL, TESS_UI_ALLOW_REAL_SESSION="1")
    assert keep_off_the_real_session(env) == {} and env["DISPLAY"] == ":0" and env["XDG_RUNTIME_DIR"] == "/run/user/1000"


def test_github_actions_is_left_alone_because_it_runs_under_its_own_display():
    env = dict(REAL, GITHUB_ACTIONS="true")
    assert keep_off_the_real_session(env) == {} and env["DISPLAY"] == ":0"


def test_a_bare_CI_variable_does_not_switch_the_guard_off():
    """An agent's shell has CI=true next to the person's real DISPLAY: the guard must still drop them."""
    env = dict(REAL, CI="true")
    removed = keep_off_the_real_session(env)
    assert set(removed) == {"DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS"} and "DISPLAY" not in env


def test_this_run_has_no_real_session_unless_allowed(monkeypatch):
    import os

    if os.environ.get("TESS_UI_ALLOW_REAL_SESSION") == "1" or os.environ.get("GITHUB_ACTIONS") == "true":
        return
    assert "WAYLAND_DISPLAY" not in os.environ and "DBUS_SESSION_BUS_ADDRESS" not in os.environ
    assert os.environ["XDG_RUNTIME_DIR"] != "/run/user/1000"


def test_a_run_renders_on_software_vulkan_where_it_is_installed_and_keeps_what_is_already_set(monkeypatch):
    monkeypatch.setattr(real_session, "software_vulkan_icd", lambda: "/usr/share/vulkan/icd.d/lvp_icd.json")
    env = dict(REAL)
    keep_off_the_real_session(env)
    assert env["VK_ICD_FILENAMES"] == "/usr/share/vulkan/icd.d/lvp_icd.json"
    env = dict(REAL, VK_ICD_FILENAMES="/elsewhere/radeon_icd.json")
    keep_off_the_real_session(env)
    assert env["VK_ICD_FILENAMES"] == "/elsewhere/radeon_icd.json"


def test_without_software_vulkan_nothing_is_pinned_and_an_allowed_real_session_is_never_pinned(monkeypatch):
    monkeypatch.setattr(real_session, "software_vulkan_icd", lambda: None)
    env = dict(REAL)
    keep_off_the_real_session(env)
    assert "VK_ICD_FILENAMES" not in env
    monkeypatch.setattr(real_session, "software_vulkan_icd", lambda: "/x/lvp_icd.json")
    env = dict(REAL, TESS_UI_ALLOW_REAL_SESSION="1")
    keep_off_the_real_session(env)
    assert "VK_ICD_FILENAMES" not in env


def test_the_lavapipe_file_is_found_in_the_first_directory_that_has_it(tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    first.mkdir()
    second.mkdir()
    (second / "lvp_icd.json").write_text("{}")
    assert software_vulkan_icd([str(first), str(second)]) == str(second / "lvp_icd.json")
    assert software_vulkan_icd([str(first)]) is None
