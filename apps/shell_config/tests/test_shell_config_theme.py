"""Light and dark: the window has a seed, so its roles have a dark scheme (without one it stayed light on a dark desktop); the Theme button cycles System, Light, Dark and the choice is kept."""

import json
import shutil

from test_shell_config_window import CONFIG
from tess_shell_config.app import build
from tess_shell_config.session import ConfigSession


def make(tmp_path, schema, **options):
    folder = tmp_path / "cfg"
    if not folder.exists():
        shutil.copytree(CONFIG, folder)
    session = ConfigSession(folder, schema, None, state_dir=tmp_path / "state")
    return build(session, reduced_motion=True, **options)


def background(built):
    for _ in range(8):
        built.window.advance(16)
    rgba, width, _ = built.window.snapshot()
    i = (500 * width + 700) * 4
    return tuple(rgba[i:i + 3])


def luminance(rgb):
    return sum(rgb) / 3


def test_a_dark_run_is_dark_and_a_light_run_is_light(tmp_path, schema):
    dark = make(tmp_path / "a", schema, dark=True)
    light = make(tmp_path / "b", schema, dark=False)
    assert luminance(background(dark)) < 80 and luminance(background(light)) > 200


def test_the_theme_button_cycles_system_light_dark_and_the_choice_is_kept(tmp_path, schema):
    built = make(tmp_path, schema)
    vm = built.viewmodel
    assert vm.theme_label.get() == "Theme: System" and built.app.dark_mode == "system"
    vm.theme_cycle()
    assert (vm.theme_label.get(), built.app.dark_mode) == ("Theme: Light", False) and luminance(background(built)) > 200
    vm.theme_cycle()
    assert (vm.theme_label.get(), built.app.dark_mode) == ("Theme: Dark", True) and luminance(background(built)) < 80
    assert json.loads((tmp_path / "state" / "settings.json").read_text())["theme"] == "dark"
    again = make(tmp_path, schema)  # the next run starts as it was left
    assert again.app.dark_mode is True and again.viewmodel.theme_label.get() == "Theme: Dark"
    vm.theme_cycle()
    assert vm.theme_label.get() == "Theme: System" and built.app.dark_mode == "system"


def test_a_flag_for_one_run_is_not_kept(tmp_path, schema):
    built = make(tmp_path, schema, dark=True)
    assert built.app.dark_mode is True
    assert not (tmp_path / "state" / "settings.json").exists() or json.loads((tmp_path / "state" / "settings.json").read_text()).get("theme") == "system"
