"""0.3.4 (#83): a component's look lives in its stylesheet.

Every built-in `<Name>_Component.yaml` is structure; its look is in `<Name>_Stylesheet.yaml`, a list of `{id: <part>, style: {...}}` rules whose
values may be the component's `{{ parameters }}`.
"""

from pathlib import Path

import pytest
import yaml

from tess_ui.spec import expand_components_to_spec
from tess_ui.spec.expand import _parts_of

BUILTIN = Path(__file__).resolve().parent.parent / "src" / "tess_ui" / "spec" / "components"
SHEETS = sorted(BUILTIN.glob("*_Stylesheet.yaml"))


def _node(spec, node_id):
    stack = [spec]
    while stack:
        node = stack.pop()
        if node.get("id") == node_id:
            return node
        stack.extend(node.get("children") or [])
    raise KeyError(node_id)


def test_there_is_a_stylesheet_for_most_built_in_components():
    assert len(SHEETS) >= 70


@pytest.mark.parametrize("sheet", SHEETS, ids=lambda p: p.name)
def test_a_built_in_stylesheet_names_parts_its_component_has(sheet):
    name = sheet.name.removesuffix("_Stylesheet.yaml")
    fragment = yaml.safe_load((BUILTIN / f"{name}_Component.yaml").read_text(encoding="utf-8"))
    rules = yaml.safe_load(sheet.read_text(encoding="utf-8"))["styles"]
    assert {rule["id"] for rule in rules} <= _parts_of(fragment)
    assert all(set(rule) == {"id", "style"} for rule in rules)


@pytest.mark.parametrize("sheet", SHEETS, ids=lambda p: p.name)
def test_a_built_in_fragment_keeps_no_style_of_its_own(sheet):
    name = sheet.name.removesuffix("_Stylesheet.yaml")
    assert "style:" not in (BUILTIN / f"{name}_Component.yaml").read_text(encoding="utf-8")


def test_a_component_is_styled_by_its_stylesheet():
    spec = expand_components_to_spec("id: root\nkind: Container\nchildren:\n"
                                     "  - {id: b, component: ButtonFilled, with: {label: Go, width: 120, height: 40, corner_radius: 20}}\n")
    assert _node(spec, "b")["style"]["background"] == "primary"
    assert _node(spec, "b")["style"]["width"] == 120  # a parameter, filled in the stylesheet
    assert _node(spec, "b.label")["style"]["foreground"] == "on_primary"


def test_a_conditional_in_a_stylesheet_follows_the_parameters():
    def tab(selected):
        spec = expand_components_to_spec(f"id: root\nkind: Container\nchildren:\n"
                                         f"  - {{id: t, component: TabsItem, with: {{label: A, width: 90, selected: {selected}}}}}\n")
        return _node(spec, "t.label")["style"]["foreground"]

    assert (tab("true"), tab("false")) == ("primary", "on_surface_variant")
