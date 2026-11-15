# Time picker

*Selection and input*

## In Material Design 3

A time picker lets the user choose an hour and a minute on a dial, with an AM/PM selector in a 12-hour
format.

## In Tesserae

Four pieces. `TimePickerDial` is a Tesserae control (`TimePickerDial`): `Hour`, `Minute` and `Mode` (`hour` or `minute`; letting go on an hour moves on to the
minutes unless `Auto_Advance` is off; the arrow keys step the hour by one or the minute by five, and a screen reader can increment and decrement it). `PeriodSelector` is a view: two 40 pixel halves, `Period` `AM` or `PM` (two-way), with an `On_Change` handler for after a choice; it is one Tab stop and the up and down arrows move and choose.
`TimeInput` is a view: an hour field, a colon, a minute field and, in 12-hour time, a period selector, where `Hour` and `Minute` are two-way and a number that does
not fit is left out (the fields are filled from the time when they appear). `TimePicker` is the dialog of Material 3.

`TimePicker`'s `Open` is two-way (Escape and a press on the scrim close it). `Hour` (0 to 23) and `Minute` are two-way and change only when OK is pressed; Cancel, Escape and the
scrim leave them. `Twelve` (the default) is 12-hour time with a dial and a period selector; `Twelve: false` opens straight on the typed fields, with no dial and no keyboard
button. `On_Ok` is called after OK.

The picker shows the time as an hour and a minute you press to choose which the dial sets, the period selector, the 256 pixel dial, a keyboard button that
swaps the dial for the typed fields (and back), and Cancel and OK. Reopening it starts from the time as it then is. Not built: a 24-hour dial with an inner ring,
limits on the times that can be chosen, and the times as a locale writes them.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `TimePicker { ... }`. A file of the same name in your project replaces it.

### `TimePicker`

The Material 3 modal time picker: a dialog with the time at the top (an hour and a minute you press to choose which the dial sets, and an AM / PM selector), a 256 pixel dial, a keyboard button that swaps the dial for typed fields, and Cancel and OK. `Hour` (0 to 23) and `Minute` are two-way and change only when OK is pressed; Cancel, Escape and a press on the scrim leave them. `Open` is two-way. `On_Ok` is called after OK. 24-hour time has no dial here (the face is the twelve hours): `Twelve: false` opens straight on the typed fields.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Open` | `bool` | `false` | Whether the picker is showing. Two-way: give it a bare reference and the view writes it back. |
| `Hour` | `int` | `0` | 0 to 23; set by OK. Two-way: give it a bare reference and the view writes it back. |
| `Minute` | `int` | `0` | 0 to 59; set by OK. Two-way: give it a bare reference and the view writes it back. |
| `Twelve` | `bool` | `true` | 12-hour time with a dial and an AM / PM selector; otherwise only the typed fields. |
| `Title` | `str` | `"Select time"` | The small heading. |
| `On_Ok` | `handler` |  | Called after OK has set hour and minute. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `panel` (Container), `heading` (Text), `header` (Container), `hour_button` (Container), `hour_text` (Text), `colon` (Text), `minute_button` (Container), `minute_text` (Text), `period` (PeriodSelector), `dial` (TimePickerDial), `fields` (TimeInput), `footer` (Container), `mode_button` (IconButton), `spacer` (Container), `cancel` (Button), `ok` (Button).

Its look is in [`TimePicker_Stylesheet.tdl`](../stylesheets/time-pickers/time-picker.md).

### `PeriodSelector`

The AM / PM selector of a time picker (Material 3): two 40 pixel halves in a 52 pixel wide, 1 pixel `outline` frame with 8 pixel corners. The chosen half is `tertiary_container`. `Period` is "AM" or "PM" and a press writes it back. One Tab stop on the chosen half; the up and down arrows move and choose.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Period` | `AM` or `PM` | `AM` | The half of the day. Two-way: give it a bare reference and the view writes it back. |
| `Disabled` | `bool` | `false` | Dimmed and not pressable. |
| `On_Change` | `handler` |  | Called after a press or an arrow key has chosen a half. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `half` (Container), `label` (Text).

Its look is in [`PeriodSelector_Stylesheet.tdl`](../stylesheets/time-pickers/period-selector.md).

### `TimePickerDial`

The clock face of a time picker.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Hour` | `float` |  | 0 to 23; a press keeps the half of the day it is in. Two-way. |
| `Minute` | `float` |  | 0 to 59, in fives on the face. Two-way. |
| `Mode` | `hour` or `minute` | `hour` | Which hand the face shows and sets; letting go in hour mode moves on to minutes. Two-way. |
| `Auto_Advance` | `bool` | `true` | Letting go in hour mode moves on to the minutes. |
| `Label` | `str` |  | What a screen reader calls it. |

## Using it

```tdl
Container {
  Name: alarm
  Style { Width: 480, Height: 520 }
  Children {
    TimePicker {
      Open: <| choosing |>
      Hour: <| alarm_hour |>
      Minute: <| alarm_minute |>
      On_Ok: alarm_set
    }
    TimeInput {
      Hour: <| alarm_hour |>
      Minute: <| alarm_minute |>
    }
    PeriodSelector {
      Period: <| half |>
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import time_picker_dial

dial = time_picker_dial(app.window, hour=9, minute=30)
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# TimePicker_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: TimePicker
    Part: panel
    Style { Background: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Controls](../guide/controls.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
