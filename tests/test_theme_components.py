"""M57 (#10): a theme's `components:` reach the Python widget factories. A factory names the component its root is (`component_of`: `card.elevated`,
`fab.small`, `dialog`); the cascade gives that node the corner radius and elevation of its `components:` entry (the variant's, then the component's), over
the shipped view's own. A node that names no component, an app's own view included, is untouched.
"""

import pytest
from helpers import elevation
from tess_re import Window

from tess_ui import Theme, View
from tess_ui.spec.cascade import component_key
from tess_ui.widgets import card, fab

SEED = (0x67, 0x50, 0xA4, 0xFF)
CUSTOM = {"components": {"card.elevated": {"corner_radius": 4, "elevation": "level_5"},
                         "dialog": {"corner_radius": "small"},
                         "fab.small": {"corner_radius": 2}}}


@pytest.mark.parametrize("key, parts", [
    ("card.elevated", ("card", "elevated")), ("button.filled_tonal", ("button", "filled_tonal")), ("fab.small", ("fab", "small")),
    ("dialog", ("dialog", None)), ("top_app_bar", ("top_app_bar", None)), ("extended_fab", ("extended_fab", None)),
])
def test_component_key(key, parts):
    assert component_key(key) == parts


def _view(key, **theme):
    view = View({"id": "w", "kind": "Rect", "component_of": key, "style": {"width": 200, "height": 100, "corner_radius": 12, "background": "primary"}},
                theme_seed=SEED, **theme)
    view.window.advance(16)
    return view


def test_a_custom_themes_entry_shapes_a_node_that_names_its_component():
    plain, themed = _view("card.elevated"), _view("card.elevated", custom_theme_spec=CUSTOM)
    assert themed.root.get("corner_radius") == 4.0 and elevation(themed.root) == 5
    assert plain.root.get("corner_radius") == 12.0  # the node's own


def test_the_variant_entry_wins_then_the_component_entry():
    theme = {"components": {"card": {"corner_radius": 20}, "card.elevated": {"corner_radius": 6}}}
    assert _view("card.elevated", custom_theme_spec=theme).root.get("corner_radius") == 6.0
    assert _view("card.outlined", custom_theme_spec=theme).root.get("corner_radius") == 20.0  # no card.outlined entry: card's


def test_a_theme_change_reapplies_it():
    view = _view("card.elevated")
    view.set_theme(theme_seed=SEED, custom_theme_spec=CUSTOM)
    assert view.root.get("corner_radius") == 4.0 and elevation(view.root) == 5
    view.set_theme(theme_seed=SEED)
    assert view.root.get("corner_radius") != 4.0


def test_a_plain_node_is_untouched():
    view = View({"id": "r", "kind": "Rect", "style": {"width": 10, "height": 10, "corner_radius": 9,
                                                      "background": "#112233"}},
                theme_seed=SEED, custom_theme_spec={"components": {"rect": {"corner_radius": 1}}})
    assert view.root.get("corner_radius") == 9.0


def test_widgets_take_their_themes_entries_and_follow_a_new_theme():
    window = Window(width=400, height=300)
    themed = Theme.resolve(theme_seed=SEED, custom_theme_spec=CUSTOM)
    widget = card(window, 200, 100, variant="elevated", theme=themed)
    assert widget.node.get("corner_radius") == 4.0 and elevation(widget.node) == 5
    widget.set_theme(Theme.resolve(theme_seed=SEED))
    assert widget.node.get("corner_radius") != 4.0
    small = fab(window, "add", size="small", theme=themed)
    assert small.node.get("corner_radius") == 2.0


def test_fab_sizes_keep_md3s_shapes_under_the_default_theme():
    window = Window(width=400, height=300)
    radii = {size: fab(window, "add", size=size).node.get("corner_radius") for size in ("small", "default", "large")}
    assert radii == {"small": 12.0, "default": 16.0, "large": 28.0}
