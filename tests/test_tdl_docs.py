"""0.3.4 (#83): the TDL reference page is written from the schemas.

`docs/api/tdl.md` comes from `tools/generate_tdl_docs.py`. It must be what the generator writes now, no key on it may be left without a description, every
widget must be in its table, and what it shows must be TDL (`Title_Case` keys, `<| |>` slots), never the YAML of the older language.
"""

import importlib.util
import re
from pathlib import Path

import pytest

pytest.importorskip("tess_dl", reason="the generators read the shipped .tdl files, which needs tess_dl (Python 3.14)")

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "docs" / "api" / "tdl.md"


def _generator():
    spec = importlib.util.spec_from_file_location("generate_tdl_docs", ROOT / "tools" / "generate_tdl_docs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_page_is_what_the_generator_writes():
    assert PAGE.read_text(encoding="utf-8") == _generator().render(), \
        "docs/api/tdl.md is out of date: run `python tools/generate_tdl_docs.py`"


def test_the_old_page_is_gone():
    assert not (ROOT / "docs" / "api" / "yaml.md").exists()


def test_every_key_has_a_description():
    empty = [line for line in PAGE.read_text(encoding="utf-8").splitlines() if re.match(r"^\| `.*\| +\|$", line)]
    assert not empty, "keys with no description:\n" + "\n".join(empty)


def test_every_widget_the_registry_and_the_shipped_views_have_is_in_the_table():
    from tess_ui.shipped import shipped_views
    from tess_ui.spec import widgets

    page = PAGE.read_text(encoding="utf-8")
    for name in [*widgets.names(), *shipped_views()]:
        assert re.search(rf"^\| (\[)?`{name}`", page, re.M), name


def test_every_node_key_is_described():
    from tess_ui.spec import widgets

    page = PAGE.read_text(encoding="utf-8")
    generator = _generator()
    for key in set(widgets._UNIVERSAL) - generator.NOT_KEYS:
        assert f"| `{generator.tdl_format.key(key)}` |" in page, key


def test_the_page_shows_tdl_and_not_yaml():
    page = PAGE.read_text(encoding="utf-8")
    assert "```yaml" not in page and "{{" not in page
    stubs = re.findall(r"^```(?:text|tdl)\n(.*?)^```", page, re.M | re.S)
    assert stubs
    for stub in stubs:
        for line in stub.splitlines():
            found = re.match(r"\s*([A-Za-z_<>]+)(?::| \{)", line)
            if found and not found.group(1).startswith("<"):
                assert found.group(1)[0].isupper(), f"a key that is not Title_Case: {line!r}"


def test_the_whole_file_example_is_a_view_that_loads():
    """The one whole document on the page is read by the real front end (the docs examples test reads every ```tdl block, this one is here too so a change to the
    generator cannot leave it out)."""
    from doc_blocks import load

    block = re.search(r"^```tdl\n(.*?)^```", PAGE.read_text(encoding="utf-8"), re.M | re.S)
    assert block
    assert load(block.group(1))[0] == "view"
