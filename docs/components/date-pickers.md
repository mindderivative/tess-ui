# Date picker

*Selection and input*

## In Material Design 3

A date picker lets the user pick a date from a month grid. Today is outlined, the chosen day is a filled
circle, and days of the neighbouring months are dimmed.

## In Tesserae

Two views Tesserae ships: `DatePickerDay` (one day, in all its states) and `DatePicker` (the modal dialog).

`DatePicker`'s `Open` is two-way (Escape and a press on the scrim close it). `Date` is text, `year-month-day` ("2026-10-09", or empty for none), also two-way, and it changes only
when OK is pressed. The days before `Earliest` and after `Latest` are disabled, `Week_Starts` is `sunday` (the default) or `monday`, and `On_Ok` is called after OK.

The dialog shows the chosen date in `headline_large` and a keyboard button that swaps the grid for a typed field (`####-##-##`; text that is not a real day is left out), the month with arrows between months, the
weekday initials, six weeks of days, and Cancel and OK. Today is outlined, the chosen day is a `primary` circle, and the days of the months either side are faint and move
the view to their month when pressed. The arrow keys move around the grid. A `DatePickerDay` has `Day`, `Selected`, `Today`, `Outside` and `Disabled`. The dates are worked out with
the expression language's `date_add_days`, `date_weekday`, `days_in_month`, `format_date` and `current_date`, which are there for any view. Not built: a range picker,
a docked picker under a field, month and year selectors, Page Up and Page Down by month, and the names of the months and days in another language.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `DatePicker { ... }`. A file of the same name in your project replaces it.

### `DatePicker`

The Material 3 modal date picker: a dialog with the chosen date at the top (and a button that swaps the grid for a typed field), the month with arrows to move between months, the weekday initials and a grid of six weeks of `DatePickerDay`s, and Cancel and OK. `Date` is a text `year-month-day` ("2026-10-09", or empty for none) and is two-way, changing only when OK is pressed; `Open` is two-way (Escape and a press on the scrim close it). `Earliest` and `Latest` bound the days that can be chosen; `Week_Starts` is `sunday` (the default) or `monday`. Today is outlined. Days of the months either side show faintly and choosing one moves to its month. The arrows move the focus around the grid. `On_Ok` is called after OK.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Open` | `bool` | `false` | Whether the picker is showing. Two-way: give it a bare reference and the view writes it back. |
| `Date` | `str` |  | The date, year-month-day; set by OK. Two-way: give it a bare reference and the view writes it back. |
| `Earliest` | `str` |  | The first date that can be chosen, year-month-day; empty for no limit. |
| `Latest` | `str` |  | The last date that can be chosen, year-month-day; empty for no limit. |
| `Week_Starts` | `sunday` or `monday` | `sunday` | Which day the weeks start on. |
| `Title` | `str` | `"Select date"` | The small heading. |
| `On_Ok` | `handler` |  | Called after OK has set the date. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `panel` (Container), `heading` (Text), `header` (Container), `chosen` (Text), `header_filler` (Container), `mode_button` (IconButton), `line` (Divider), `month_bar` (Container), `month` (Text), `month_filler` (Container), `previous` (IconButton), `next` (IconButton), `weekdays` (Container), `weekday` (Container), `initial` (Text), `grid` (Container), `day` (DatePickerDay), `entry` (TextField), `footer` (Container), `cancel` (Button), `ok` (Button).

Its look is in [`DatePicker_Stylesheet.tdl`](../stylesheets/date-pickers/date-picker.md).

### `DatePickerDay`

One day of a date picker (Material 3): a 48 pixel target holding a 40 pixel circle with the number in `body_large`. Today is outlined in `primary`; the selected day is a `primary` circle with `on_primary` text; a day outside the month shown is `on_surface_variant`; a disabled day is dimmed. It is pressable; `Handlers: {On_Click: ...}` on the call is what a press does. One view for a day's states: normal, selected, today, outside the month and disabled.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Day` | `str` |  | The number shown. |
| `Selected` | `bool` | `false` | The chosen day. |
| `Today` | `bool` | `false` | Today. |
| `Outside` | `bool` | `false` | A day of the month before or after the one shown. |
| `Disabled` | `bool` | `false` | Dimmed, and not pressable. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `circle` (Container), `number` (Text).

Its look is in [`DatePickerDay_Stylesheet.tdl`](../stylesheets/date-pickers/date-picker-day.md).

## Using it

```tdl
Container {
  Name: booking
  Style { Width: 480, Height: 640 }
  Children {
    DatePicker {
      Open: <| choosing |>
      Date: <| day |>
      Earliest: "2026-01-01"
    }
    DatePickerDay {
      Day: "7"
      Selected: true
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import date_picker_day

day = date_picker_day(app.window, 7, selected=True)
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# DatePicker_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: DatePicker
    Part: panel
    Style { Background: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
