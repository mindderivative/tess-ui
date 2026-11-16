"""M37 Phase 1: Tesserae's MD3 tokens (`tess_ui.tokens`) match `tess_re`'s,
checked against `tess_re` 0.3.4's answers, recorded (M43, `tests/reference.py`)
since 0.3.5 removes them (`tess_re` D7)."""

import struct

import pytest
import tess_re

import reference
from tess_ui import tokens

SEEDS = [(0x67, 0x50, 0xA4), (0xB3, 0x26, 0x1E), (0x00, 0x6A, 0x60), (0xFF, 0xB0, 0x00),
         (0x21, 0x96, 0xF3), (0x00, 0x00, 0x00), (0xFF, 0xFF, 0xFF), (0x7D, 0x52, 0x60)]


def _tre_roles(seed, dark, custom=None):
    def ask():
        window = tess_re.Window(width=10, height=10)
        window.set_theme((*seed, 0xFF), dark=dark, custom_theme_spec=custom)
        return {role: window.theme.role(role) for role in tokens.ROLES}
    return reference.tess_re(ask)


def _tre_read(spec, prop, show=False, **kwargs):
    """A `tess_re` `View` of `spec`'s node `r`'s `prop`, recorded."""
    def ask():
        view = tess_re.View(spec=spec, **kwargs)
        if show:
            tess_re.Window.from_view(view, width=10, height=10, title="t")
        return view.node("r").get(prop)
    return reference.tess_re(ask)


@pytest.mark.parametrize("dark", [False, True], ids=["light", "dark"])
@pytest.mark.parametrize("seed", SEEDS, ids=[bytes(s).hex() for s in SEEDS])
def test_every_role_matches_tre(seed, dark):
    assert tokens.color_scheme((*seed, 0xFF), dark) == _tre_roles(seed, dark)


def test_colors_overrides_match_tre():
    custom = {"colors": {"primary": "#00FF00", "surface": "rgb(10, 20, 30)"}}
    ours = tokens.resolve_scheme((0x67, 0x50, 0xA4, 0xFF), False, None, custom)
    assert ours == _tre_roles((0x67, 0x50, 0xA4), False, custom)


def test_seed_precedence_matches_tre_views():
    """`theme_seed`, else the custom theme's `seed:`, else the default
    theme's -- `tess_re`'s `View` rule."""
    red, blue = {"seed": "#FF0000"}, {"seed": "#0000FF"}
    purple = (0x67, 0x50, 0xA4, 0xFF)
    assert tokens.resolve_scheme(purple, False, blue, red) == tokens.color_scheme(purple)
    assert tokens.resolve_scheme(None, False, blue, red) == tokens.color_scheme((255, 0, 0, 255))
    assert tokens.resolve_scheme(None, False, blue, None) == tokens.color_scheme((0, 0, 255, 255))
    assert tokens.resolve_scheme(None, False, None, None) is None
    # and a View built with each resolves `primary` to the same colour
    for kwargs, ours in [
        ({"theme_seed": purple, "custom_theme_spec": red}, tokens.color_scheme(purple)),
        ({"custom_theme_spec": red, "default_theme_spec": blue}, tokens.color_scheme((255, 0, 0, 255))),
    ]:
        spec = {"id": "r", "kind": "Rect", "style": {"width": 1, "height": 1, "background": "primary"}}
        assert _tre_read(spec, "fill", show=True, **kwargs) == ours["primary"]


def test_an_unknown_role_in_colors_is_an_error():
    with pytest.raises(ValueError, match="unknown color role 'primry'"):
        tokens.resolve_scheme((0, 0, 0, 255), False, None, {"colors": {"primry": "#000000"}})


@pytest.mark.parametrize("name", sorted(tokens.SHAPES))
def test_shape_tokens_match_tre(name):
    spec = {"id": "r", "kind": "Rect", "style": {"width": 1, "height": 1, "background": "#000000", "corner_radius": name}}
    assert _tre_read(spec, "corner_radius") == tokens.shape(name)


@pytest.mark.parametrize("name", sorted(tokens.ELEVATION_LEVELS))
def test_elevation_levels_match_tre(name):
    spec = {"id": "r", "kind": "Rect", "style": {"width": 1, "height": 1, "background": "#000000", "elevation": name}}
    assert _tre_read(spec, "elevation") == tokens.elevation(name)


def test_unknown_tokens_are_none_as_in_tre():
    assert tokens.shape("enormous") is None and tokens.elevation("level_6") is None and tokens.type_style("huge") is None


@pytest.mark.parametrize("role", sorted(tokens.TYPE_SCALE))
def test_type_roles_match_tre(role):
    def ask():
        window = tess_re.Window(width=10, height=10)
        window.set_theme((0x67, 0x50, 0xA4, 0xFF))
        return window.theme.typography(role)
    style = tokens.type_style(role)
    f32 = lambda x: struct.unpack("f", struct.pack("f", x))[0]  # tess_re stores these as f32
    assert reference.tess_re(ask) == (style.font_family, style.font_weight, style.font_size, f32(style.line_height))


def test_elevation_shadows_reproduce_tres_geometry():
    """`tess_re`'s own docs give level 1 as exactly this pair; the others
    follow `engine-render`'s key/ambient formulas."""
    assert tokens.elevation_shadows(0) == []
    assert tokens.elevation_shadows(1) == [((0, 0, 0, 77), 0.0, 1.0, 2.0, 0.0), ((0, 0, 0, 38), 0.0, 1.0, 3.0, 1.0)]
    assert tokens.elevation_shadows(3) == [((0, 0, 0, 77), 0.0, 1.0, 3.0, 0.0), ((0, 0, 0, 38), 0.0, 4.0, 8.0, 3.0)]
    assert tokens.elevation_shadows(5) == [((0, 0, 0, 77), 0.0, 4.0, 4.0, 0.0), ((0, 0, 0, 38), 0.0, 8.0, 12.0, 6.0)]


def test_elevation_shadows_are_accepted_by_tre():
    window = tess_re.Window(width=10, height=10)
    box = window.create("box", width=10, height=10, shadows=tokens.elevation_shadows(2))
    assert box.get("shadows") == tokens.elevation_shadows(2)


def test_a_bad_theme_seed_reports_the_shared_colour_wording():
    """The colour parser is `tess_utils.parse_color`; tess-ui's themes pass its errors through."""
    with pytest.raises(ValueError, match="unknown color identifier"):
        tokens.resolve_scheme(None, False, None, {"seed": "notacolor"})
    with pytest.raises(ValueError, match="invalid color"):
        tokens.resolve_color("rgb(1,2)")
