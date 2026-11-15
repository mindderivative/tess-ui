# Button groups

*Actions*

## In Material Design 3

A button group lays related buttons side by side, with an even gap, so they read as one set of choices.

## In Tesserae

`ButtonGroup` is a view Tesserae ships (`ButtonGroup_View.tdl`): `Button`s side by side, one for each of `Items`.

The `Mode` says what the buttons are: `none` (the default) is a row of actions, and the value of the one last pressed goes to `Chosen` (nothing needs to be bound);
`single` is a choice of one, with `Selected` its value; `multiple` is a set, with `Selected` the list of chosen values. Each item is `{Value, Label}` and optionally
`{Icon, Disabled}`. `Variant` and `Size` are `Button`'s and go to every button. By default the buttons stand 8 pixels apart; `Connected: true` makes the gap 2
pixels with 4 pixel inner corners, and `Orientation: vertical` makes a column.

In `single` mode a chosen button is a toggle that is on, and the arrow keys move the choice; `multiple` toggles each button and the arrows only move the
focus. There is one Tab stop. Not built: the pressed button widening and its neighbours giving way, and an overflow button.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `ButtonGroup { ... }`. A file of the same name in your project replaces it.

### `ButtonGroup`

The Material 3 button group: buttons that behave as a set. `Mode: none` is a row of actions (the last one pressed goes to `Chosen`), `single` is a choice of one (`Selected` is the chosen value) and `Multiple` a set (`Selected` is the list of chosen values). `Connected: true` joins the buttons with a 2 pixel gap and square inner corners; otherwise they stand 8 pixels apart. One Tab stop; the arrow keys move the focus (and, for `single`, the choice). The look of each button is Button's: `Variant` and `Size` pass to every one.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Items` | `list` | `[]` | The buttons, each {value, label} and optionally {icon, disabled}. |
| `Mode` | `none` or `single` or `multiple` | `none` | none: actions; single: one chosen; multiple: any number chosen. |
| `Selected` | `any` |  | single: the chosen value; multiple: the list of chosen values. Two-way: give it a bare reference and the view writes it back. |
| `Chosen` | `any` |  | none: the value of the button last pressed. Two-way: give it a bare reference and the view writes it back. |
| `Variant` | `filled` or `tonal` or `elevated` or `outlined` or `text` | `filled` | Passed to every button. |
| `Size` | `xs` or `s` or `m` or `l` or `xl` | `s` | Passed to every button. |
| `Connected` | `bool` | `false` | Joined, with square inner corners. |
| `Orientation` | `horizontal` or `vertical` | `horizontal` | A row, or a column. |
| `Disabled` | `bool` | `false` | No button can be pressed. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `item` (Button).

## Using it

```tdl
Container {
  Name: calendar
  Style { Flex_Direction: vertical, Gap: 12, Padding: 16, Width: 360, Height: 160 }
  Children {
    ButtonGroup {
      Mode: single
      Connected: true
      Variant: tonal
      Selected: <| range |>
      Items {
        Item { Value: day, Label: Day }
        Item { Value: week, Label: Week }
        Item { Value: month, Label: Month }
      }
    }
    ButtonGroup {
      Chosen: <| last_action |>
      Items {
        Item { Value: copy, Label: Copy, Icon: home }
        Item { Value: paste, Label: Paste }
      }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import button_group

group = button_group(app.window, ["Day", "Week", "Month"], 90, 40, on_click=viewmodel.pick)
```

## See also

- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
