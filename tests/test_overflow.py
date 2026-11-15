"""#260 (part of #257): `style.overflow` -- `hidden` and `visible`, another way to write `clip_children`."""

import pytest

from tess_ui import App, ViewModel


class VM(ViewModel):
    views = "main"


def opened(tmp_path, panel_style, background="surface"):
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(f"""---
TDL: 0.2
Name: main
---
Container {{
  Name: main
  Style {{ Width: 300, Height: 200, Background: {background} }}
  Children {{
    Container {{
      Name: panel
      Style {{ Position: absolute, X: 0, Y: 0, Width: 100, Height: 100, Background: surface_container_highest, {panel_style} }}
      Children {{
        Rect {{
          Name: spill
          Style {{ Position: absolute, X: 80, Y: 20, Width: 60, Height: 40, Background: primary }}
        }}
      }}
    }}
  }}
}}
""")
    app = App(root=tmp_path, theme_seed=(0x67, 0x50, 0xA4, 0xFF), dark=False)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    view.window.advance(16)
    return app, view


def pixel(view, x, y):
    rgba, width, _ = view.window.snapshot()
    i = (y * width + x) * 4
    return tuple(rgba[i:i + 3])


def is_color(view, found, role, tolerance=3):
    want = tuple(round(c) for c in view.theme.role(role))[:3]
    return all(abs(a - b) <= tolerance for a, b in zip(found, want))


def test_hidden_cuts_what_spills_out_of_the_node(tmp_path):
    app, view = opened(tmp_path, "Overflow: hidden")
    assert view.node("root.panel").get("clip_children") is True
    assert is_color(view, pixel(view, 90, 40), "primary")                      # inside the panel
    assert not is_color(view, pixel(view, 120, 40), "primary")                 # the part that spills past it is cut


def test_visible_lets_it_spill(tmp_path):
    app, view = opened(tmp_path, "Overflow: visible")
    assert view.node("root.panel").get("clip_children") is False
    assert is_color(view, pixel(view, 120, 40), "primary")


def test_it_is_the_same_as_clip_children(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    _, by_overflow = opened(tmp_path / "a", "Overflow: hidden")
    _, by_clip = opened(tmp_path / "b", "Clip_Children: true")
    assert by_overflow.node("root.panel").get("clip_children") is by_clip.node("root.panel").get("clip_children") is True
    assert pixel(by_overflow, 120, 40) == pixel(by_clip, 120, 40)


def test_the_engine_style_has_clip_children_and_not_our_name_for_it():
    from tess_ui.spec.layout import engine_style

    engine = engine_style("n", {"overflow": "hidden"})
    assert engine["clip_children"] is True and "overflow" not in engine
    assert engine_style("n", {"overflow": "visible"})["clip_children"] is False


def test_saying_both_the_same_way_is_fine(tmp_path):
    app, view = opened(tmp_path, "Overflow: hidden, Clip_Children: true")
    assert view.node("root.panel").get("clip_children") is True


@pytest.mark.parametrize("style", ["Overflow: hidden, Clip_Children: false", "Clip_Children: true, Overflow: visible"])
def test_saying_both_differently_is_an_error_that_names_both(tmp_path, style):
    with pytest.raises(Exception, match=r"style\.overflow: \w+ and style\.clip_children: \w+ disagree; say one of them"):
        opened(tmp_path, style)


@pytest.mark.parametrize("value", ["scroll", "auto", "clip", "true"])
def test_a_value_that_is_not_hidden_or_visible_is_refused_naming_the_node(tmp_path, value):
    with pytest.raises(Exception, match="style.overflow must be one of hidden, visible"):
        opened(tmp_path, f"Overflow: {value}")


def test_a_node_that_does_not_say_it_keeps_what_it_had(tmp_path):
    app, view = opened(tmp_path, "Padding: 0")
    assert view.node("root.panel").get("clip_children") is False


def test_overflow_is_not_the_texts_own_overflow_property(tmp_path):
    """A Text has an `overflow` property (clip or ellipsis); the style field of the same name is the other thing."""
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Main_View.tdl").write_text("""---
TDL: 0.2
Name: main
---
Container {
  Name: main
  Style { Width: 300, Height: 200 }
  Children {
    Text {
      Name: t
      Text: "a long line of text"
      Overflow: ellipsis
      Wrap: none
      Typography_Role: body_medium
      Style { Foreground: on_surface, Width: 40, Overflow: hidden }
    }
  }
}
""")
    app = App(root=tmp_path)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    view.window.advance(16)
    t = view.node("root.t")
    assert t.get("clip_children") is True and t.get("overflow") == "ellipsis"
