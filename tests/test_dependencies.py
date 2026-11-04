"""Tesserae's dependency on `tess_re` is one exact release, not a range.

Moving to a new `tess_re` line is a new Tesserae line, which the user starts, and `>=` alone would let pip (and CI) take a new line the day it's released, as it
took 0.4.4 and, later, 0.5.8 (it changed hit testing and broke four tests in CI). The engine's 0.6 line is the one that is `import tess_re`; Tesserae 0.6.0 is built on it.
"""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _project():
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def test_tess_re_is_pinned_to_the_release_the_suite_was_run_on():
    engine = next(d for d in _project()["dependencies"] if d.startswith("tesserae-engine"))
    found = re.fullmatch(r"tesserae-engine==(0\.6\.\d+)", engine)
    assert found, f"{engine!r}: pin one exact tess_re release (==0.6.x); a new one is tried by the user first, then this moves"


def test_tesserae_is_0_5():
    assert _project()["version"].startswith("0.5.")
