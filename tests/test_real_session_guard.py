"""A bare local test run keeps the person's own session out of reach (tests/real_session.py, applied by tests/conftest.py and apps/shell_config/tests/conftest.py)."""

from real_session import REAL_SESSION_VARIABLES, keep_off_the_real_session

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


def test_ci_is_left_alone_because_it_runs_under_its_own_display():
    env = dict(REAL, CI="true")
    assert keep_off_the_real_session(env) == {} and env["DISPLAY"] == ":0"


def test_this_run_has_no_real_session_unless_allowed(monkeypatch):
    import os

    if os.environ.get("TESS_UI_ALLOW_REAL_SESSION") == "1" or os.environ.get("CI"):
        return
    assert "WAYLAND_DISPLAY" not in os.environ and "DBUS_SESSION_BUS_ADDRESS" not in os.environ
    assert os.environ["XDG_RUNTIME_DIR"] != "/run/user/1000"
