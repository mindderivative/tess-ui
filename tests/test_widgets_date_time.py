"""`tess_ui.widgets.time_picker_dial`, a Tesserae control since M40. The
rest of the Date & Time category is in `tests/test_date_time.py` (M42).
"""

from tess_re import Window

from tess_ui.widgets import time_picker_dial


def test_time_picker_dial_returns_a_dial_control():
    from tess_ui import controls

    window = Window(width=400, height=300)
    dial = time_picker_dial(window, hour=9, minute=30, size=200)
    assert isinstance(dial, controls.TimePickerDial) and (dial.hour.get(), dial.minute.get()) == (9, 30)
    assert dial.node.get("width") == 200.0 and dial.node.parent() == window.root


