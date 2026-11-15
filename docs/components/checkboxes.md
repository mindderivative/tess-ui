# Checkbox

*Selection and input*

## In Material Design 3

A checkbox lets the user select one or more items from a set, or turn an option on or off. It has a 40dp
state layer around an 18dp box.

## In Tesserae

`Checkbox` is one of Tesserae's controls (`tess_ui.controls.Checkbox`). Give `Checked` a bare reference and a press writes it back. It has three
states: on, off, and empty (`null`), which is neither: a dash in a filled box, for a parent of some checked children. A press turns an empty one on.

The `Label` sits beside the box and is part of what you press: pressing the text toggles the box and gives it the focus. `Error` draws it in the error colours, and a
disabled one is dimmed and does nothing. `Handlers { On_Change: ... }` runs after the user changes it (not when the bound value changes).

The colour is `Style.Foreground`. The 18 pixel box sits in a 48 pixel target with a 40 pixel state layer; Tab reaches it, and Space or Enter toggles it.

## How it is built

### `Checkbox`

A box that is on or off.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Checked` | `bool` |  | true, false, or empty (null) for a box that is neither: a parent of some checked children. Two-way. |
| `Disabled` | `bool` |  |  |
| `Error` | `bool` |  | Drawn in the error colours. |
| `Label` | `str` |  | Text beside it that is part of what you press, and what a screen reader calls it. |

Its `Style` also takes `Foreground`.

## Using it

```tdl
Container {
  Name: terms
  Style { Flex_Direction: vertical, Gap: 4, Width: 280, Height: 160, Padding: 16 }
  Children {
    Checkbox {
      Checked: <| all_read |>
      Label: "I have read the terms"
      Error: <| show_error |>
    }
    Checkbox {  # empty while only some are on
      Checked: <| some_read |>
      Label: "Select all"
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import checkbox

agree = checkbox(app.window, (0xFF, 0xFF, 0xFF, 0xFF), 48, 48, checked=False)
agree.checked.get()
```

## See also

- [Controls](../guide/controls.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
