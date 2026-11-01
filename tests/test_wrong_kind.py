"""#294: a file whose content is another kind than its name says is named as what it looks like, and what to call it.

The hint comes from the root keys alone and always says "looks like". A file that matches no kind keeps the message it had.
"""

import pytest

from tesserae.project import kind_of_keys
from tesserae.spec.cascade import check_stylesheet, check_theme
from tesserae.spec.nodes import LoadError, load_marked, parse_view
from tesserae.spec.rules import RuleSheet
from tesserae.spec.themes import load_stylesheet, load_theme


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


def view_error(text, file="Brand_View.yaml"):
    with pytest.raises(LoadError) as caught:
        parse_view(text, file)
    return str(caught.value)


def test_a_view_that_holds_a_stylesheet_says_so_and_what_to_name_it():
    text = view_error("styles:\n  - {widget: Text, style: {foreground: red}}\n")
    assert "a node needs a 'widget:'" in text  # the old message, first
    assert "this looks like a stylesheet: name it Brand_Stylesheet.yaml" in text


def test_a_view_that_holds_a_theme_says_so_and_what_to_name_it():
    assert "this looks like a theme: name it Brand_Theme.yaml" in view_error("seed: '#6750A4'\n")
    assert "this looks like a theme: name it Brand_Theme.yaml" in view_error("styles: []\ncolors: {}\n")


def test_a_view_with_no_name_to_go_by_says_what_to_put_in_the_name():
    text = view_error("seed: '#6750A4'\n", file="<view>")
    assert "this looks like a theme: name it <Name>_Theme.yaml" in text


def test_a_view_that_matches_no_kind_keeps_its_message():
    text = view_error("label: x\nsize: 3\n")
    assert text.endswith("(its keys are: label, size)")
    assert "looks like" not in text


def test_the_older_syntax_message_is_kept_and_has_no_hint():
    text = view_error("kind: Container\nstyles: []\n")
    assert "'kind:' is not a key in 0.5.0" in text
    assert "looks like" not in text


def test_a_nested_node_with_styles_is_not_a_misnamed_file():
    text = view_error("widget: Container\nchildren:\n  - styles: []\n")
    assert "a node needs a 'widget:'" in text
    assert "looks like" not in text


def test_a_stylesheet_that_holds_a_view_says_so():
    with pytest.raises(LoadError) as caught:
        RuleSheet.of(load_marked("widget: Container\n", "App_Stylesheet.yaml"), "App_Stylesheet.yaml")
    text = str(caught.value)
    assert "a stylesheet has only 'styles:', not 'widget'" in text
    assert "this looks like a view: name it App_View.yaml" in text


def test_a_stylesheet_that_holds_a_theme_says_so():
    with pytest.raises(LoadError) as caught:
        RuleSheet.of(load_marked("seed: '#6750A4'\nstyles: []\n", "Brand_Stylesheet.yaml"), "Brand_Stylesheet.yaml")
    assert "this looks like a theme: name it Brand_Theme.yaml" in str(caught.value)


def test_a_stylesheet_that_matches_no_kind_keeps_its_message():
    with pytest.raises(LoadError) as caught:
        RuleSheet.of(load_marked("rules: []\n", "App_Stylesheet.yaml"), "App_Stylesheet.yaml")
    assert "looks like" not in str(caught.value)


def test_a_plain_stylesheet_dict_is_checked_with_the_same_hint():
    with pytest.raises(ValueError, match=r"looks like a view: name it <Name>_View.yaml"):
        check_stylesheet({"widget": "Container"})
    with pytest.raises(ValueError, match=r"looks like a theme: name it <Name>_Theme.yaml"):
        check_stylesheet({"seed": "#6750A4", "styles": []})
    with pytest.raises(ValueError) as caught:
        check_stylesheet({"rules": []})
    assert "looks like" not in str(caught.value)


def test_a_theme_that_holds_a_view_says_so():
    with pytest.raises(ValueError, match=r"looks like a view: name it <Name>_View.yaml"):
        check_theme({"widget": "Container"})


def test_a_theme_file_that_holds_a_view_names_the_file_to_give_it(tmp_path):
    file = tmp_path / "Brand_Theme.yaml"
    file.write_text("widget: Container\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"unknown field `widget`.*this looks like a view: name it Brand_View.yaml"):
        load_theme(file)


@pytest.mark.parametrize("text, expect", [
    ("widget: Container\n", "looks like a view: name it Brand_View.yaml"),
    ("seed: '#6750A4'\nstyles: []\n", "looks like a theme: name it Brand_Theme.yaml"),
])
def test_a_stylesheet_file_of_another_kind_names_the_file_to_give_it(tmp_path, text, expect):
    file = tmp_path / "Brand_Stylesheet.yaml"
    file.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=expect):
        load_stylesheet(file)


def test_a_stylesheet_file_that_matches_no_kind_is_left_to_the_later_check(tmp_path):
    file = tmp_path / "Brand_Stylesheet.yaml"
    file.write_text("rules: []\n", encoding="utf-8")
    assert load_stylesheet(file) == {"rules": []}  # no hint, and `load_stylesheet` itself still does not judge it


def test_a_theme_that_is_a_theme_and_a_stylesheet_that_is_one_pass(tmp_path):
    (tmp_path / "Brand_Theme.yaml").write_text("seed: '#6750A4'\nstyles: []\n", encoding="utf-8")
    (tmp_path / "App_Stylesheet.yaml").write_text("styles: []\n", encoding="utf-8")
    assert load_theme(tmp_path / "Brand_Theme.yaml")["seed"] == "#6750A4"
    assert load_stylesheet(tmp_path / "App_Stylesheet.yaml") == {"styles": []}


def test_a_stylesheet_with_an_unknown_key_is_not_told_it_looks_like_a_stylesheet():
    with pytest.raises(LoadError) as caught:
        RuleSheet.of(load_marked("styles: []\nrules: []\n", "App_Stylesheet.yaml"), "App_Stylesheet.yaml")
    assert "a stylesheet has only 'styles:', not 'rules'" in str(caught.value)
    assert "looks like" not in str(caught.value)
