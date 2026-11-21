"""An App with no seed has no colour scheme, so `dark` cannot change anything: it says so once, where dark is asked for."""

from loguru import logger

from tess_ui import App

SEED = (0x67, 0x50, 0xA4, 0xFF)


def test_dark_true_without_a_seed_warns_once(tmp_path):
    handle_seen = []
    handle = logger.add(lambda m: handle_seen.append(m.record["message"]) if m.record["level"].name == "WARNING" else None)
    try:
        app = App(root=tmp_path, dark=True)
        app.set_dark(False)
        app.set_dark(True)
    finally:
        logger.remove(handle)
    assert len([m for m in handle_seen if "no `theme_seed`" in m]) == 1


def test_a_seed_or_the_default_system_mode_does_not_warn(tmp_path):
    seen = []
    handle = logger.add(lambda m: seen.append(m.record["message"]) if m.record["level"].name == "WARNING" else None)
    try:
        App(root=tmp_path, dark=True, theme_seed=SEED)
        App(root=tmp_path, dark=False)
        App(root=tmp_path)
    finally:
        logger.remove(handle)
    assert [m for m in seen if "theme_seed" in m] == []
