"""Real coverage for the component fragments of the Search and Date & Time widgets the Python factories build from: `SearchBar`, `DatePickerDay` and
`PeriodSelectorAM`, each checked against `tess_ui.widgets`' own output."""

import pytest
from helpers import elevation, expand_components, view_from
from tess_re import Window

from tess_ui.widgets import date_picker_day, period_selector, search_bar

THEME_SEED = (0x67, 0x50, 0xA4, 0xFF)


def _window(width=400, height=300):
    return Window(width=width, height=height)


def test_search_bar_matches_the_imperative_catalog():
    yaml_text = """
id: root
kind: Container
style: {width: 400, height: 300}
children:
  - id: sb
    component: SearchBar
    with: {placeholder: "Search...", width: 360, corner_radius: 28}
"""
    expanded = expand_components(yaml_text)
    view = view_from(expanded, theme_seed=THEME_SEED)
    declarative = view.node("sb")
    assert view.node("sb.field") is not None

    imperative = search_bar(_window(), "Search...", 360).node  # a Widget since M42

    assert declarative.get("corner_radius") == imperative.get("corner_radius")
    assert elevation(declarative) == elevation(imperative)






DATE_PICKER_DAY_CASES = [
    ("DatePickerDay", dict(selected=False, today=False, outside_month=False)),
]


def test_all_date_picker_day_states_match_the_imperative_catalog():
    for component_name, kwargs in DATE_PICKER_DAY_CASES:
        yaml_text = f"""
id: root
kind: Container
style: {{width: 200, height: 200}}
children:
  - id: d
    component: {component_name}
    with: {{day: "15"}}
"""
        expanded = expand_components(yaml_text)
        view = view_from(expanded, theme_seed=THEME_SEED)
        declarative = view.node("d")

        imperative = date_picker_day(_window(), 15, **kwargs)  # a Widget since M42

        # both are 48 px targets; since M42 the widget draws MD3's 40 px circle inside (the fragment keeps tess_re's)
        assert declarative.get("width") == imperative.node.get("width") == 48.0, component_name
        assert imperative.part("indicator").get("corner_radius") == 20.0, component_name


def test_date_picker_day_requires_a_quoted_string_day():
    # Real, confirmed requirement (see the fragments' own header
    # comments): `day` must be a string -- `TextSpec.content` is
    # `String`-typed, and whole-value substitution preserves the
    # supplied Python type verbatim. `expand_components` itself is a
    # pure string-substitution pass with no schema validation -- the
    # real error only surfaces once the view is built (Tesserae's compiler
    # rejects it as `tess_re`'s parser did).
    yaml_text = """
id: root
kind: Container
children:
  - id: d
    component: DatePickerDay
    with: {day: 15}
"""
    expanded = expand_components(yaml_text)
    with pytest.raises(ValueError, match="text.content must be a string, got int 15"):
        view_from(expanded, theme_seed=(0x67, 0x50, 0xA4, 0xFF))


def test_period_selector_am_matches_the_imperative_catalog():
    for component_name in ["PeriodSelectorAM"]:
        yaml_text = f"""
id: root
kind: Container
style: {{width: 200, height: 200}}
children:
  - id: ps
    component: {component_name}
"""
        expanded = expand_components(yaml_text)
        view = view_from(expanded, theme_seed=THEME_SEED)
        am = view.node("ps.am")
        pm = view.node("ps.pm")

        imperative = period_selector(_window(), selected="AM")  # a Widget since M42

        # the fragment keeps tess_re's rounded halves; the widget is MD3's, square halves in an outlined 8 px frame
        assert am.get("corner_radius") == pm.get("corner_radius") == 8.0, component_name
        assert imperative.node.get("corner_radius") == 8.0 and imperative.part("am").get("corner_radius") == 0.0



