"""A screen change is announced politely through the window (AC-RTV-10); an engine without `announce` stays silent."""

from tess_ui.app import announce_screen


class Spoken:
    def __init__(self):
        self.said = []

    def announce(self, text, politeness="polite"):
        self.said.append((text, politeness))


def test_the_screen_title_is_announced_once_politely_AC_RTV_10():
    window = Spoken()
    announce_screen(window, "Settings")
    assert window.said == [("Settings", "polite")]


def test_an_engine_without_announce_is_silent():
    announce_screen(object(), "Settings")
