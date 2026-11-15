"""Which front end reads a file, and which flavour of the shipped files Tesserae loads.

A file is read by its suffix: `.tdl` by the TDL front ends (they need `tess_dl`, an optional extra until the cutover), anything else by the YAML ones.

Tesserae ships every view, stylesheet and its default theme in both forms. The library loads the `.tdl` ones, so the whole shipped set goes through the TDL
front ends, and falls back to the YAML ones when `tess_dl` is not installed (Python before 3.14). `TESS_UI_SHIPPED=yaml` forces the YAML ones, to compare the
two or to bisect a difference; `TESS_UI_SHIPPED=tdl` asks for the TDL ones and is what the default already is. The variable is read every time it is asked,
so a test can set it.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

__all__ = ["ENV", "is_tdl", "require_tdl", "shipped_ext", "shipped_flavour", "tdl_available"]

ENV = "TESS_UI_SHIPPED"


def is_tdl(file: str | Path) -> bool:
    """Whether `file` (a path or a name) is read by the TDL front ends: its name ends in `.tdl`."""
    return str(file).endswith(".tdl")


def tdl_available() -> bool:
    """Whether `tess_dl`, which the TDL front ends need, can be imported."""
    return importlib.util.find_spec("tess_dl") is not None


def require_tdl(file: str | Path) -> None:
    """Raises a `ValueError` that says what to install when `file` is TDL and `tess_dl` is missing."""
    if not tdl_available():
        raise ValueError(f"{file}: reading a TDL file needs the tess-dl package (Python 3.14): `pip install 'tesserae-ui[tdl]'`")


def shipped_flavour() -> str:
    """`"tdl"` or `"yaml"`: the form of the shipped files the library loads (see the module docstring)."""
    wanted = os.environ.get(ENV, "").strip().lower()
    if wanted not in ("", "tdl", "yaml"):
        raise ValueError(f"{ENV} is `tdl` or `yaml`, not {wanted!r}")
    return "yaml" if wanted == "yaml" or not tdl_available() else "tdl"


def shipped_ext() -> str:
    """The file extension of the shipped files the library loads: `".tdl"` or `".yaml"`."""
    return f".{shipped_flavour()}"
