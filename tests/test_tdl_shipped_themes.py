"""The default theme Tesserae ships is `default_theme.tdl`; the examples' themes are `.tdl` only, and each loads and checks."""

from pathlib import Path

import pytest

from tess_ui.spec.themes import load_theme

ROOT = Path(__file__).parent.parent
EXAMPLES = sorted(ROOT.joinpath("examples").rglob("*_Theme.tdl"))


def test_the_default_theme_is_tdl_and_the_examples_themes_are_tdl_only():
    assert (ROOT / "src" / "tess_ui" / "spec" / "default_theme.tdl").is_file()
    assert not (ROOT / "src" / "tess_ui" / "spec" / "default_theme.yaml").exists()
    assert len(EXAMPLES) == 8
    assert not list(ROOT.joinpath("examples").rglob("*_Theme.yaml"))


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_an_example_theme_loads_and_checks(path):
    assert "seed" in load_theme(path)
