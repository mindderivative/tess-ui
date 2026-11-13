"""A bare test run never reaches the person's own session. Shared by `tests/conftest.py` and `apps/shell_config/tests/conftest.py`: each applies the guard before anything else runs,
and `ensure()` does it once however many conftest files ask.

Tests open windows (`App.run(max_frames=...)`, the example apps, the built executable) and write and read the OS clipboard through tess_re. With the person's DISPLAY,
WAYLAND_DISPLAY and session bus in the environment they would do that on their desktop: a window on it, their clipboard overwritten. So a local run drops those variables (the
tests that need a display skip, as on CI's Linux) and points the per-user config, cache and state at a private folder. `TESS_UI_ALLOW_REAL_SESSION=1` allows it, for a hand-run on
purpose; CI (`CI` is set) is left alone, because its jobs run under their own `xvfb-run` display.
"""

import os
import tempfile

REAL_SESSION_VARIABLES = ("DISPLAY", "WAYLAND_DISPLAY", "WAYLAND_SOCKET", "DBUS_SESSION_BUS_ADDRESS", "XDG_SESSION_ID", "XDG_SESSION_TYPE")


def keep_off_the_real_session(environ=os.environ):
    """Remove the real session from `environ` and return what was removed (empty when nothing was, or when it is allowed)."""
    if environ.get("TESS_UI_ALLOW_REAL_SESSION") == "1" or environ.get("CI"):
        return {}
    removed = {name: environ.pop(name) for name in REAL_SESSION_VARIABLES if name in environ}
    private = tempfile.mkdtemp(prefix="tess-ui-tests-")
    for name in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME", "XDG_DATA_HOME", "XDG_RUNTIME_DIR"):
        environ[name] = os.path.join(private, name.lower())
        os.makedirs(environ[name], mode=0o700, exist_ok=True)
    environ.setdefault("TESS_UI_STATE_DIR", os.path.join(private, "state"))
    return removed


_removed = None


def ensure():
    """Apply the guard to `os.environ` the first time; return what it removed (later calls return the same answer and change nothing)."""
    global _removed
    if _removed is None:
        _removed = keep_off_the_real_session()
    return _removed
