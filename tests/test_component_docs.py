"""0.3.4 (#83): the component and stylesheet pages are written by `tools/generate_component_docs.py`.

The pages must be what the generator writes now, and every example on them
must work: each TDL usage loads as a view, and each Python one runs.
"""

import importlib.util
from pathlib import Path

import pytest
import yaml  # the generator's own data file (tools/component_docs.yaml) is YAML: tooling data read by tools/ only

pytest.importorskip("tess_dl", reason="the generators read the shipped .tdl files, which needs tess_dl (Python 3.14)")

from tess_ui import App

ROOT = Path(__file__).resolve().parent.parent
SEED = (0x67, 0x50, 0xA4, 0xFF)


def _generator():
    spec = importlib.util.spec_from_file_location("generate_component_docs", ROOT / "tools" / "generate_component_docs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GENERATOR = _generator()
DATA = yaml.safe_load(GENERATOR.DATA.read_text(encoding="utf-8"))
ENTRIES = [pytest.param(entry, id=entry["slug"]) for entry in DATA["components"]]


def test_the_pages_are_what_the_generator_writes():
    pages = GENERATOR.build()
    stale = [p.relative_to(ROOT).as_posix() for p, text in pages.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    existing = {p for folder in (GENERATOR.DOCS / "components", GENERATOR.DOCS / "stylesheets") for p in folder.rglob("*.md")}
    assert not stale and not (existing - set(pages)), \
        f"out of date: {stale or sorted(existing - set(pages))}: run `python tools/generate_component_docs.py`"


def test_every_shipped_view_is_on_exactly_one_page():
    listed = sorted(name for entry in DATA["components"] for name in entry.get("views", []))
    assert listed == GENERATOR.shipped_views()


def test_the_generators_read_the_tdl_files_and_no_yaml_twin():
    assert GENERATOR.shipped_views() and all(p.suffix == ".tdl" for p in GENERATOR.VIEWS.glob("*_View.tdl"))
    assert "yaml" not in GENERATOR.View("Button").path.suffix and GENERATOR.View("Button").sheet_path.suffix == ".tdl"


def test_a_view_left_off_every_page_is_refused():
    with pytest.raises(SystemExit, match="not listed"):
        GENERATOR.check_coverage(DATA, GENERATOR.shipped_views() + ["NoSuchView"])


@pytest.mark.parametrize("entry", [p for p in ENTRIES if p.values[0].get("usage_view")])
def test_a_tdl_usage_example_loads_as_a_view(entry):
    """The example on a component page is a whole view in TDL (its metadata block is left off, as on every docs page) and it loads against the shipped views."""
    from doc_blocks import load

    kind, _ = load(entry["usage_view"])
    assert kind == "view"


class _Anything:
    """A stand-in for the ViewModel and widgets an example refers to."""

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


@pytest.mark.parametrize("entry", [p for p in ENTRIES if p.values[0].get("python")])
def test_a_python_example_runs(entry, tmp_path, monkeypatch):
    from PIL import Image

    Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(tmp_path / "cat.png")
    monkeypatch.chdir(tmp_path)
    app = App(width=800, height=600)
    from tess_ui.widgets import button

    names = {"app": app, "viewmodel": _Anything(), "save": button(app.window, "Save", 80, 40),
             "left": button(app.window, "L", 80, 40), "right": button(app.window, "R", 80, 40)}
    exec(compile(entry["python"], f"<{entry['slug']}>", "exec"), names)


def test_every_page_links_to_its_stylesheets_and_back():
    pages = GENERATOR.build()
    for path, text in pages.items():
        if path.parent.parent == GENERATOR.DOCS / "stylesheets":
            slug = path.parent.name
            assert f"../../components/{slug}.md" in text


def test_a_stylesheet_with_no_view_of_its_own_still_gets_its_page():
    """`Link` is a built-in widget with a `Link_Stylesheet.tdl` and no `Link_View.tdl` (#291): its page exists and its component page links to it."""
    pages = GENERATOR.build()
    page = pages[GENERATOR.DOCS / "stylesheets" / "links" / "link.md"]
    assert "Link_Stylesheet.tdl" in page and "State: visited" in page
    assert "../stylesheets/links/link.md" in pages[GENERATOR.DOCS / "components" / "links.md"]
    written = {(p.parent.name, p.stem) for p in pages if p.parent.parent == GENERATOR.DOCS / "stylesheets"}
    for sheet in (ROOT / "src" / "tess_ui" / "views").glob("*_Stylesheet.tdl"):
        name = sheet.name.removesuffix("_Stylesheet.tdl")
        assert any(stem == GENERATOR._kebab(name) for _, stem in written), f"{sheet.name} has no stylesheet page"
