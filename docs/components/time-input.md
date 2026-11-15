# Time input

*Selection and input*

## In Material Design 3

A time input field is a numeric field for the hour or the minute, used in the time picker's keyboard mode.

## In Tesserae

`TimeInput` is a view Tesserae ships (`TimeInput_View.tdl`): two outlined `TextField`s, 96 pixels wide, for the hour and the minute, a colon between them and, in
12-hour time, a `PeriodSelector`. `Hour` (0 to 23) and `Minute` are two-way. The fields take two digits (`Mask: "##"`); a number that does not fit (1 to 12 in 12-hour
time, 0 to 23 otherwise, and 0 to 59 for the minute) is left out until it does. The fields are filled from the time when the input appears and follow what is typed after
that. The time picker shows it in its keyboard mode.

In Python, `time_input_field` is one numeric field of Material 3's: 96 by 72 pixels, a centred two-digit numeral, `unit` `hour` or `minute`. Its `Value` is a `Signal`;
typing a number in range sets it, and the up and down arrows (and a screen reader's increment and decrement) step it, wrapping.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `TimeInput { ... }`. A file of the same name in your project replaces it.

### `TimeInput`

The keyboard form of a time picker (Material 3's "input mode"): an hour field, a colon, a minute field and, in 12-hour time, an AM / PM selector. `Hour` (0 to 23) and `Minute` (0 to 59) are two-way; the fields take the digits, and a number that does not fit is left out until it does. The fields are filled from `Hour` and `Minute` when the input appears, and follow what is typed after that. `Twelve` shows 1 to 12 and the period selector, otherwise the hour is 0 to 23.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Hour` | `int` | `0` | 0 to 23. Two-way: give it a bare reference and the view writes it back. |
| `Minute` | `int` | `0` | 0 to 59. Two-way: give it a bare reference and the view writes it back. |
| `Twelve` | `bool` | `true` | 12-hour time with an AM / PM selector. |
| `Disabled` | `bool` | `false` | Dimmed and not editable. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `hour_field` (TextField), `colon` (Text), `minute_field` (TextField), `period_selector` (PeriodSelector).

Its look is in [`TimeInput_Stylesheet.tdl`](../stylesheets/time-input/time-input.md).

## Using it

```tdl
Container {
  Name: alarm_time
  Style { Width: 360, Height: 120, Padding: 16 }
  Children {
    TimeInput {
      Hour: <| alarm_hour |>
      Minute: <| alarm_minute |>
      Twelve: false
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import time_input_field

hour = time_input_field(app.window, 9, unit="hour")
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# TimeInput_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: TimeInput
    Part: colon
    Style { Foreground: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
