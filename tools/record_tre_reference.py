"""M43: records `tess_re`'s answers for the parity tests (`tests/reference.py`)
into `tests/reference/*.json`.

Run it on `tess_re` 0.3.4 -- the last release with the `View`, `Signal` and
window theme the answers come from -- whenever a parity test asks `tess_re`
something new:

    TESS_RE_SOURCE_DIR=... .venv/bin/python tools/record_tre_reference.py

It runs the parity tests with `TESS_UI_RECORD_TESS_RE=1`, which makes each
`reference.tess_re(fn)` call `fn` and keep its answer. The files are written
only if every test passes (a mismatch is never written in as `tess_re`'s
answer); each module's file is replaced whole.

The corpora a recording builds keep every question asked before, exactly
as it was asked (`reference.previous`), and add only what's new, so an
existing answer never changes: the tree corpus reuses each recorded
case's spec and frames, and the binding corpus each recorded expression.
Fragments and views `tess_re` 0.3.4 can't build are left out (`Tabs`, whose
divider is `width: "100%"`, which 0.3.4's `View` doesn't take).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULES = ["test_tree_parity", "test_spec_build", "test_tokens", "test_theme_object",
           "test_view", "test_clickable", "test_wide_gamut"]


def main() -> int:
    import tess_re

    missing = [name for name in ("View", "Signal") if not hasattr(tess_re, name)]
    if missing or not hasattr(tess_re.Window, "set_theme"):
        print(f"tess_re has no {', '.join(missing) or 'Window.set_theme'}: record in an environment with tre 0.3.4 "
              "(0.3.5 has no View, Signal or window theme to ask)", file=sys.stderr)
        return 2
    env = {**os.environ, "TESS_UI_RECORD_TESS_RE": "1"}
    args = [sys.executable, "-m", "pytest", "-q", *(f"tests/{m}.py" for m in MODULES), *sys.argv[1:]]
    result = subprocess.run(args, cwd=ROOT, env=env)
    if result.returncode == 0:
        print(f"recorded tess_re's answers in {ROOT / 'tests/reference'}")
    else:
        print("a test failed, so nothing was written", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
