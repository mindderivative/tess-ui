"""#294: a file whose content is another kind than its name says is named as what it looks like, and what to call it.

The hint comes from the root block alone (the root keys, for a plain dict) and always says "looks like". A file that matches no kind keeps the message it had.
"""

import pytest

from tess_ui.project import kind_of_keys, kind_of_tdl
from tess_ui.spec.cascade import check_stylesheet, check_theme
from tess_ui.spec.nodes import LoadError, parse_view
from tess_ui.spec.rules import RuleSheet
from tess_ui.spec.tdl_stylesheet import load_marked_tdl_stylesheet
from tess_ui.spec.themes import load_stylesheet, load_theme

META = "---\nTDL: 0.2\nName: Brand\n---\n"
THEME = 'Theme { Seed: "#6750A4" }\n'


@pytest.mark.parametrize("keys, kind", [
    (["widget", "name"], "view"),
    (["styles"], "stylesheet"),
    (["seed", "colors"], "theme"),
    (["styles", "seed"], "theme"),  # a theme may hold styles:, so a theme key decides
    (["dark"], "theme"),
    (["typography"], "theme"),
    (["components"], "theme"),
    (["tesserae", "styles"], "stylesheet"),  # the first-line marker is not content
    (["widget", "styles"], "view"),
    (["label", "size"], None),
    ([], None),
])
def test_the_root_keys_say_what_a_file_looks_like(keys, kind):
    assert kind_of_keys(keys) == kind


@pytest.mark.parametrize("root, kind", [
    ("Container { }", "view"),
    ("Styles { }", "stylesheet"),
    ("Theme { }", "theme"),
    ("Label { Size: 3 }", "view"),  # any other word heads a widget
    ("", None),
])
def test_the_root_block_says_what_a_tdl_file_looks_like(root, kind):
    assert kind_of_tdl(META + root) == kind


def view_error(root, file="Brand_View.tdl"):
    with pytest.raises(LoadError) as caught:
        parse_view(META + root, file)
    return str(caught.value)


def test_a_view_that_holds_a_stylesheet_says_so_and_what_to_name_it():
    text = view_error("Styles {\n  Rule { Widget: Text, Style { Foreground: red } }\n}\n")
    assert "a view's root block is a widget" in text  # the plain message, first
    assert "this looks like a stylesheet: name it Brand_Stylesheet.tdl" in text


def test_a_view_that_holds_a_theme_says_so_and_what_to_name_it():
    assert "this looks like a theme: name it Brand_Theme.tdl" in view_error(THEME)
    assert "this looks like a theme: name it Brand_Theme.tdl" in view_error('Theme { Seed: "#6750A4", Colors { } }\n')


def test_a_view_with_no_name_to_go_by_says_what_to_put_in_the_name():
    text = view_error(THEME, file="x.tdl")
    assert "this looks like a theme: name it <Name>_Theme.tdl" in text


def test_a_view_that_matches_no_kind_keeps_its_message():
    text = view_error("Label { Size: 3 }\n")
    assert "no widget named 'Label'" in text
    assert "looks like" not in text


def test_a_nested_block_named_styles_is_not_a_misnamed_file():
    text = view_error("Container { Children { Styles { } } }\n")
    assert "no widget named 'Styles'" in text
    assert "looks like" not in text


def test_a_stylesheet_that_holds_a_view_is_told_what_a_stylesheet_is():
    with pytest.raises(LoadError) as caught:
        RuleSheet.of(load_marked_tdl_stylesheet(META + "Container { }\n", "App_Stylesheet.tdl"), "App_Stylesheet.tdl")
    assert "a stylesheet is one Styles block of Rule blocks, not 'Container'" in str(caught.value)


def test_a_stylesheet_with_an_unknown_block_is_not_told_it_looks_like_anything():
    with pytest.raises(LoadError) as caught:
        RuleSheet.of(load_marked_tdl_stylesheet(META + "Styles { Rules { } }\n", "App_Stylesheet.tdl"), "App_Stylesheet.tdl")
    assert "Styles holds Rule blocks, got 'Rules'" in str(caught.value)
    assert "looks like" not in str(caught.value)


def test_a_plain_stylesheet_dict_is_checked_with_the_same_hint():
    with pytest.raises(ValueError, match=r"looks like a view: name it <Name>_View\."):
        check_stylesheet({"widget": "Container"})
    with pytest.raises(ValueError, match=r"looks like a theme: name it <Name>_Theme\."):
        check_stylesheet({"seed": "#6750A4", "styles": []})
    with pytest.raises(ValueError) as caught:
        check_stylesheet({"rules": []})
    assert "looks like" not in str(caught.value)


def test_a_theme_that_holds_a_view_says_so():
    with pytest.raises(ValueError, match=r"looks like a view: name it <Name>_View\."):
        check_theme({"widget": "Container"})


def test_a_theme_file_that_holds_a_view_names_the_file_to_give_it(tmp_path):
    file = tmp_path / "Brand_Theme.tdl"
    file.write_text(META + "Container { }\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"this looks like a view: name it Brand_View.tdl"):
        load_theme(file)


@pytest.mark.parametrize("root, expect", [
    ("Container { }\n", "looks like a view: name it Brand_View.tdl"),
    (THEME, "looks like a theme: name it Brand_Theme.tdl"),
])
def test_a_stylesheet_file_of_another_kind_names_the_file_to_give_it(tmp_path, root, expect):
    file = tmp_path / "Brand_Stylesheet.tdl"
    file.write_text(META + root, encoding="utf-8")
    with pytest.raises(ValueError, match=expect):
        load_stylesheet(file)


def test_a_stylesheet_file_with_no_root_block_has_no_hint(tmp_path):
    file = tmp_path / "Brand_Stylesheet.tdl"
    file.write_text(META, encoding="utf-8")
    with pytest.raises(LoadError, match="no root block") as caught:
        load_stylesheet(file)
    assert "looks like" not in str(caught.value)


def test_a_theme_that_is_a_theme_and_a_stylesheet_that_is_one_pass(tmp_path):
    (tmp_path / "Brand_Theme.tdl").write_text(META + THEME, encoding="utf-8")
    (tmp_path / "App_Stylesheet.tdl").write_text(META + "Styles { }\n", encoding="utf-8")
    assert load_theme(tmp_path / "Brand_Theme.tdl")["seed"] == "#6750A4"
    assert load_stylesheet(tmp_path / "App_Stylesheet.tdl") == {"styles": []}
