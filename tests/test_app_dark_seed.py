"""An app with no seed is drawn in the baseline scheme, light or dark (AC-TH-9, AC-TH-11): without a seed there was no scheme and `dark` changed nothing."""

from tess_ui import App, tokens

VIEW = "---\nTDL: 0.2\nName: main\n---\nContainer { Name: main, Style { Width: 200, Height: 100, Background: surface } }\n"


def corner_pixel(tmp_path, dark):
    (tmp_path / "Views").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(VIEW)
    app = App(root=tmp_path, width=200, height=100, dark=dark)
    view = app.open_view("Main")
    app.show("main")
    for _ in range(6):
        view.window.advance(16)
    rgba, width, _ = view.window.snapshot()
    return tuple(rgba[:3])


def test_an_app_with_no_seed_gets_the_baseline_surface_in_dark_and_light_keeps_the_engines_AC_TH_9(tmp_path):
    dark = corner_pixel(tmp_path / "d", True)
    light = corner_pixel(tmp_path / "l", False)
    assert dark == (0x14, 0x12, 0x18)  # #141218, exact
    # light keeps the engine's own baseline roles, which are the 2021 table (#FFFBFE); the spec's AC-TH-9 says #FEF7FF (the 2022 table): TUI-062, a finding of its own
    assert light == tuple(tokens.BASELINE["surface"][:3])


def test_set_dark_reaches_the_surfaces_of_an_app_with_no_seed_AC_TH_11(tmp_path):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Main_View.tdl").write_text(VIEW)
    app = App(root=tmp_path, width=200, height=100, dark=False)
    view = app.open_view("Main")
    app.show("main")
    app.set_dark(True)
    for _ in range(6):
        view.window.advance(16)
    rgba, _, _ = view.window.snapshot()
    assert tuple(rgba[:3]) == (0x14, 0x12, 0x18)


def test_the_light_dark_choice_is_kept_and_a_corrupt_store_is_ignored_AC_TH_4_AC_TH_6(tmp_path):
    store = tmp_path / "state" / "theme"
    first = App(root=tmp_path, theme_store=store, dark=False)
    first.set_dark(True)
    assert store.read_text().strip() == "dark"
    again = App(root=tmp_path, theme_store=store, dark=False)  # the stored choice wins over the default
    assert again.dark_mode is True and again.dark
    again.set_dark("system")
    assert store.read_text().strip() == "system" and App(root=tmp_path, theme_store=store, dark=False).dark_mode == "system"
    store.write_text("purple")
    assert App(root=tmp_path, theme_store=store, dark=False).dark_mode is False  # ignored, no error


def test_text_the_toolkit_builds_without_a_type_role_is_body_medium(tmp_path):
    """The app declares MD3's body medium as its windows' baseline text (`set_defaults`): 14 px Roboto, not the engine's 16."""
    app = App(root=tmp_path, width=200, height=100)
    for kind in ("text", "text_input"):
        node = app.window.create(kind, **({"text": "x"} if kind == "text" else {}))
        assert (node.get("font_family"), node.get("font_weight"), node.get("font_size")) == ("Roboto", 400.0, 14.0)
