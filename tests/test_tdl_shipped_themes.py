"""Piece 5 of the TDL switch: Tesserae's own `default_theme.yaml` has its `.tdl` beside it, current, and loading to the same mapping as the YAML (kept in step until
the cutover, piece 10); the examples' themes (piece 6b) are `.tdl` only, and each loads and checks."""

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
DEFAULT = ROOT / "src" / "tess_ui" / "spec" / "default_theme.yaml"
SHIPPED = [DEFAULT]
EXAMPLES = sorted(ROOT.joinpath("examples").rglob("*_Theme.tdl"))


def test_the_default_theme_has_a_tdl_file_and_the_examples_themes_are_tdl_only():
    assert DEFAULT.with_suffix(".tdl").is_file()
    assert len(EXAMPLES) == 8
    assert not list(ROOT.joinpath("examples").rglob("*_Theme.yaml"))


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_an_example_theme_loads_and_checks(path):
    theme = load_theme_tdl_file(path)  # the file loader: includes, check_theme, fonts
    assert load_theme(path) == theme  # the app's loader picks the front end by suffix
    assert "seed" in theme


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
