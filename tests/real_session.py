"""A bare test run never reaches the person's own session. Shared by `tests/conftest.py` and `apps/shell_config/tests/conftest.py`: each applies the guard before anything else runs,
and `ensure()` does it once however many conftest files ask.

Tests open windows (`App.run(max_frames=...)`, the example apps, the built executable) and write and read the OS clipboard through tess_re. With the person's DISPLAY,
WAYLAND_DISPLAY and session bus in the environment they would do that on their desktop: a window on it, their clipboard overwritten. So a local run drops those variables (the
tests that need a display skip, as on CI's Linux) and points the per-user config, cache and state at a private folder. `TESS_UI_ALLOW_REAL_SESSION=1` allows it, for a hand-run on
purpose; GitHub Actions (`GITHUB_ACTIONS` is set) is left alone, because its jobs run under their own `xvfb-run` display. Not `CI`: that one is set by other tools too (an agent's shell has it, next to the
person's real DISPLAY and session bus), and keying on it left the guard doing nothing there.

The same run renders on Mesa's software Vulkan (lavapipe) where it is installed, as CI does, instead of on whatever GPU the machine has: the results then match CI's, and a test never
loads the person's real graphics driver. Measured on this suite: 9500 tests in 1m49 on lavapipe against 1m37 on the AMD GPU (4 workers each). A variable already set (`VK_ICD_FILENAMES`)
is kept, and `TESS_UI_ALLOW_REAL_SESSION=1` skips the pin too (a hand-run on the real GPU on purpose).
"""

import os
import tempfile

REAL_SESSION_VARIABLES = ("DISPLAY", "WAYLAND_DISPLAY", "WAYLAND_SOCKET", "DBUS_SESSION_BUS_ADDRESS", "XDG_SESSION_ID", "XDG_SESSION_TYPE")
VULKAN_ICD_DIRS = ("/usr/share/vulkan/icd.d", "/etc/vulkan/icd.d", "/usr/local/share/vulkan/icd.d")


def software_vulkan_icd(directories=VULKAN_ICD_DIRS):
    """The lavapipe ICD file, or None where Mesa's software Vulkan is not installed (macOS, Windows, a bare machine)."""
    for directory in directories:
        path = os.path.join(directory, "lvp_icd.json")
        if os.path.isfile(path):
            return path
    return None


def keep_off_the_real_session(environ=os.environ):
    """Remove the real session from `environ` and return what was removed (empty when nothing was, or when it is allowed)."""
    if environ.get("TESS_UI_ALLOW_REAL_SESSION") == "1" or environ.get("GITHUB_ACTIONS") == "true":
        return {}
    removed = {name: environ.pop(name) for name in REAL_SESSION_VARIABLES if name in environ}
    private = tempfile.mkdtemp(prefix="tess-ui-tests-")
    for name in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME", "XDG_DATA_HOME", "XDG_RUNTIME_DIR"):
        environ[name] = os.path.join(private, name.lower())
        os.makedirs(environ[name], mode=0o700, exist_ok=True)
    environ.setdefault("TESS_UI_STATE_DIR", os.path.join(private, "state"))
    icd = software_vulkan_icd()
    if icd:
        environ.setdefault("VK_ICD_FILENAMES", icd)
    return removed


_removed = None


def ensure():
    """Apply the guard to `os.environ` the first time; return what it removed (later calls return the same answer and change nothing)."""
    global _removed
    if _removed is None:
        _removed = keep_off_the_real_session()
    return _removed
