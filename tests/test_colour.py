"""#298: colour values as the colour picker holds them -- '#rrggbb' text, '#rrggbbaa' under full alpha, hue kept where the colour has none."""

import random

import pytest

from tess_ui import colour


def test_it_reads_six_and_eight_digit_hex_in_either_case_and_nothing_else():
    assert colour.parse("#336699") == (0x33, 0x66, 0x99, 255)
    assert colour.parse("#336699CC") == (0x33, 0x66, 0x99, 0xCC)
    assert colour.parse("#AbCdEf") == (0xAB, 0xCD, 0xEF, 255)
    for bad in ("", "#", "#fff", "#12345", "#1234567", "#123456789", "336699", "red", "#gg0000", " #336699", "#336699 ", None, 7, "#33669\u0661"):
        assert colour.parse(bad) is None and not colour.is_valid(bad)


def test_it_writes_lowercase_and_leaves_the_alpha_off_when_it_is_full():
    assert colour.format_hex(255, 0, 170) == "#ff00aa"
    assert colour.format_hex(255, 0, 170, 255) == "#ff00aa"
    assert colour.format_hex(255, 0, 170, 254) == "#ff00aafe"
    assert colour.format_hex(0, 0, 0, 0) == "#00000000"
    assert colour.format_hex(300, -4, 7.9) == "#ff0007"  # held to a byte


def test_a_colour_goes_through_hue_saturation_value_and_back_unchanged_for_every_kind_of_colour():
    rng = random.Random(298)
    grid = [(r, g, b) for r in range(0, 256, 15) for g in range(0, 256, 15) for b in range(0, 256, 15)]
    colours = [colour.format_hex(*c) for c in grid + [tuple(rng.randrange(256) for _ in range(3)) for _ in range(20000)]]
    colours += [colour.format_hex(*[rng.randrange(256) for _ in range(4)]) for _ in range(5000)]  # with alpha
    for text in colours:
        h, s, v, a = colour.hsva(text)
        assert colour.from_hsva(h, s, v, a) == text, text


def test_the_primaries_have_their_hues():
    assert colour.hsva("#ff0000")[:3] == (0.0, 1.0, 1.0)
    assert colour.hsva("#00ff00")[0] == 120.0
    assert colour.hsva("#0000ff")[0] == 240.0
    assert colour.hsva("#ffffff")[1:3] == (0.0, 1.0) and colour.hsva("#000000")[1:3] == (0.0, 0.0)
    assert colour.from_hsva(200, 1, 1) == "#00aaff"
    assert colour.from_hsva(360, 1, 1) == colour.from_hsva(0, 1, 1) == "#ff0000"


def test_alpha_is_a_byte_over_255_and_full_alpha_has_no_digits():
    assert colour.hsva("#ff000080")[3] == pytest.approx(128 / 255)
    assert colour.from_hsva(0, 1, 1, 128 / 255) == "#ff000080"
    assert colour.from_hsva(0, 1, 1, 1.0) == "#ff0000" and colour.from_hsva(0, 1, 1, 0.0) == "#ff000000"


def test_the_remembered_hue_is_kept_for_a_grey_or_a_black_and_for_a_colour_that_still_makes_it():
    assert colour.hsva("#000000", 200)[0] == 200  # black has no hue of its own
    assert colour.hsva("#808080", 75.5)[0] == 75.5
    assert colour.hsva("#ffffff", 0)[0] == 0
    exact = colour.from_hsva(200.37, 0.5, 0.8)
    assert colour.hsva(exact, 200.37)[0] == 200.37  # a finer hue than the text holds, while the text still agrees with it
    assert colour.hsva(exact)[0] != 200.37


def test_a_remembered_hue_the_colour_no_longer_agrees_with_gives_way_to_its_own():
    assert colour.hsva("#ff0000", 200)[0] == 0.0  # set from outside: the picker's memory is stale
    assert colour.hsva("#00ff00", 0)[0] == 120.0
    assert colour.hsva("#00ff00", 400)[0] == 120.0 and colour.hsva("#00ff00", -1)[0] == 120.0  # out of range is no memory


def test_saturation_and_value_survive_a_hue_drag_exactly():
    """A drag of the hue strip rewrites the text from the saturation and value the text gave: the byte rounding must not walk them."""
    text = colour.from_hsva(10, 0.37, 0.61)
    _, s0, v0, _ = colour.hsva(text)
    for step in range(0, 360, 3):
        text = colour.from_hsva(step * 1.0, *colour.hsva(text)[1:])
        _, s, v, _ = colour.hsva(text)
        assert (s, v) == (s0, v0), step


def test_a_channel_or_the_alpha_can_be_replaced():
    assert colour.with_channel("#336699", "red", 255) == "#ff6699"
    assert colour.with_channel("#336699", "blue", 0) == "#336600"
    assert colour.with_channel("#336699", "alpha", 128) == "#33669980"
    assert colour.with_channel("#33669980", "alpha", 255) == "#336699"
    assert colour.with_alpha("#336699", 0.5) == "#33669980" and colour.with_alpha("#33669980", 1.0) == "#336699"
    with pytest.raises(ValueError, match="channel"):
        colour.with_channel("#336699", "hue", 1)


def test_text_that_is_not_a_colour_is_refused_by_name():
    for call in (lambda: colour.hsva("blue"), lambda: colour.with_alpha("#fff", 1), lambda: colour.with_channel("nope", "red", 1)):
        with pytest.raises(ValueError, match="not a colour"):
            call()
