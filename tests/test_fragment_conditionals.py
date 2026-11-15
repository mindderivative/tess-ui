"""M55 (#8): expansion-time conditionals in component fragments, and the
text-only extended FAB they make declarable.

- `params:` entries can have defaults: `{icon: null}` is optional.
- A `children:` entry with `when: "{{ p }}"` is kept only when `p` is
  truthy after substitution.
- A value `{if: "{{ p }}", then: a, else: b}` picks one (no `else:`
  leaves the key out).
"""

import pytest
import yaml
from helpers import expand_components, view_from
from tess_re import Window

from tess_ui.spec import expand_components_to_spec
from tess_ui.spec.expand import ComponentError
from tess_ui.spec.fragments import FRAGMENTS
from tess_ui.widgets import extended_fab

THEME_SEED = (0x67, 0x50, 0xA4, 0xFF)

# The YAML text of the test fragment: `_register` reads it into the data `FRAGMENTS` holds.
FRAGMENT = """
params: [label, {icon: null}, {size: 10}]
id: root
kind: Container
style:
  width: "{{ size }}"
  padding: {if: "{{ icon }}", then: 4, else: 8}
  gap: {if: "{{ icon }}", then: 2}
children:
  - id: icon
    when: "{{ icon }}"
    kind: Icon
    icon: {name: "{{ icon }}"}
  - id: label
    kind: Text
    text: {content: "{{ label }}"}
"""


def _register(monkeypatch, fragment=FRAGMENT):
    tree = yaml.safe_load(fragment)
    monkeypatch.setitem(FRAGMENTS, "Chip", {"params": tree.pop("params"), "tree": tree})


def _expand(monkeypatch, with_, fragment=FRAGMENT):
    _register(monkeypatch, fragment)
    return expand_components_to_spec({"id": "c", "component": "Chip", "with": with_})


def _ids(spec):
    return [child["id"] for child in spec["children"]]


def test_an_optional_param_takes_its_default_and_can_be_given(monkeypatch):
    assert _expand(monkeypatch, {"label": "Hi"})["style"]["width"] == 10
    assert _expand(monkeypatch, {"label": "Hi", "size": 30})["style"]["width"] == 30


def test_when_keeps_or_drops_a_child_and_if_picks_a_value(monkeypatch):
    bare = _expand(monkeypatch, {"label": "Hi"})
    assert _ids(bare) == ["c.label"] and bare["style"]["padding"] == 8 and "gap" not in bare["style"]
    with_icon = _expand(monkeypatch, {"label": "Hi", "icon": "add"})
    assert _ids(with_icon) == ["c.icon", "c.label"] and "when" not in with_icon["children"][0]
    assert with_icon["style"]["padding"] == 4 and with_icon["style"]["gap"] == 2


@pytest.mark.parametrize("value, kept", [
    (None, False), ("", False), (False, False), (0, False), ("false", False), ("No", False), ("null", False),
    ("add", True), (True, True), (1, True), ("yes", True),
])
def test_what_counts_as_true(monkeypatch, value, kept):
    assert ("c.icon" in _ids(_expand(monkeypatch, {"label": "Hi", "icon": value}))) is kept


def test_conditionals_work_per_item_in_repeat(monkeypatch):
    _register(monkeypatch)
    spec = expand_components_to_spec({"id": "row", "kind": "Container", "children": [
        {"id": "c", "component": "Chip", "repeat": [{"label": "A", "icon": "add"}, {"label": "B"}]}]})
    first, second = spec["children"]
    assert _ids(first) == ["c.0.icon", "c.0.label"] and _ids(second) == ["c.1.label"]


def test_a_malformed_conditional_or_param_is_named(monkeypatch):
    with pytest.raises(ComponentError, match=r"Chip \('c'\): a conditional value is"):
        _expand(monkeypatch, {"label": "Hi"}, FRAGMENT.replace("then: 4, else: 8", "else: 8"))
    with pytest.raises(ComponentError, match="a conditional value is"):
        _expand(monkeypatch, {"label": "Hi"}, FRAGMENT.replace("then: 4, else: 8", "then: 4, otherwise: 8"))
    with pytest.raises(ComponentError, match=r"a `params:` entry is a name or \{name: default\}"):
        _expand(monkeypatch, {"label": "Hi"}, FRAGMENT.replace("{size: 10}", "{size: 10, colour: red}"))
    with pytest.raises(ComponentError, match=r"missing parameter\(s\) \['label'\]"):
        _expand(monkeypatch, {})  # a param with no default is still required


# -- #8: the text-only extended FAB -----------------------------------------------


VARIANTS = [("ExtendedFabSurface", "surface"), ("ExtendedFabPrimary", "primary"),
            ("ExtendedFabSecondary", "secondary"), ("ExtendedFabTertiary", "tertiary")]


@pytest.mark.parametrize("component, variant", VARIANTS)
@pytest.mark.parametrize("icon", [None, "add"])
def test_extended_fab_fragments_match_the_widget_with_and_without_an_icon(component, variant, icon):
    with_ = {"label": "Compose", "width": 160} | ({"icon": icon} if icon else {})
    view = view_from(expand_components(yaml.safe_dump(
        {"id": "root", "kind": "Container", "style": {"width": 300, "height": 100},
         "children": [{"id": "b", "component": component, "with": with_}]}, sort_keys=False)), theme_seed=THEME_SEED)
    window = Window(width=300, height=100)
    widget = extended_fab(window, "Compose", 160, icon=icon, variant=variant)
    view.window.advance(16)
    window.advance(16)
    declared = view.spec["children"][0]
    assert [c["kind"] for c in declared["children"]] == [c["kind"] for c in widget.spec["children"]]
    assert [c["kind"] for c in declared["children"]] == (["Icon", "Text"] if icon else ["Text"])
    node = view.node("b")
    assert node.get("padding_left") == widget.node.get("padding_left") == (16.0 if icon else 20.0)
    assert node.get("padding_right") == widget.node.get("padding_right") == 20.0
    label, widget_label = view.node("b.label"), widget.part("label")
    assert label.get("layout_x") - node.get("layout_x") == pytest.approx(
        widget_label.get("layout_x") - widget.node.get("layout_x"), abs=0.5)
    if icon is None:  # centred in the 160 px FAB
        centre = label.get("layout_x") + label.get("layout_width") / 2 - node.get("layout_x")
        assert centre == pytest.approx(80.0, abs=1.0)
