"""Piece 5 of the TDL switch: every real theme file (the examples' `*_Theme.yaml` and Tesserae's own `default_theme.yaml`) has its `.tdl` beside it, current, and
loading to the same mapping as the YAML. The YAML files are still what tess-ui loads; the `.tdl` files are the converter's output, kept in step until the
cutover (piece 10)."""

from pathlib import Path

import pytest

pytest.importorskip("tess_dl", reason="the TDL front end needs tess_dl (Python 3.14)")

import yaml  # noqa: E402

from tess_ui.migrate_tdl import _canon  # noqa: E402
from tess_ui.migrate_tdl_theme import convert_theme, theme_stem  # noqa: E402
from tess_ui.spec import marker  # noqa: E402
from tess_ui.spec.expand import _normalize_scalars  # noqa: E402
from tess_ui.spec.tdl_theme import load_theme_tdl, load_theme_tdl_file  # noqa: E402
from tess_ui.spec.themes import load_theme  # noqa: E402

ROOT = Path(__file__).parent.parent
SHIPPED = sorted([*ROOT.joinpath("examples").rglob("*_Theme.yaml"), ROOT / "src" / "tess_ui" / "spec" / "default_theme.yaml"])


def test_every_real_theme_has_a_tdl_file_and_no_tdl_theme_is_left_without_its_yaml():
    yaml_names = {p.with_suffix(".tdl") for p in SHIPPED}
    tdl_names = {*ROOT.joinpath("examples").rglob("*_Theme.tdl"), ROOT / "src" / "tess_ui" / "spec" / "default_theme.tdl"}
    assert len(SHIPPED) == 9
    assert yaml_names == tdl_names


@pytest.mark.parametrize("path", SHIPPED, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_the_tdl_file_is_what_the_converter_writes_now_and_loads_to_the_yaml_mapping(path):
    text = path.read_text(encoding="utf-8")
    tdl = path.with_suffix(".tdl")
    written = tdl.read_bytes().decode("utf-8")
    assert written == convert_theme(text, theme_stem(path.name), path.name).text, f"{tdl.name} is stale: run `tesserae migrate-tdl --write`"
    expected = _normalize_scalars(marker.strip(yaml.safe_load(text)))
    got = load_theme_tdl(written, tdl.name)
    assert got == expected
    assert _canon(got) == _canon(expected)
    assert load_theme_tdl_file(tdl) == load_theme(path)  # the file loader: same dict, same checks
