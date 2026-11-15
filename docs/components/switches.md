# Switch

*Selection and input*

## In Material Design 3

A switch toggles one setting on or off, and takes effect at once. It has a track and a thumb that grows when
it is on.

## In Tesserae

`Switch`, a Tesserae control: a 52 by 32 pixel track and a handle that slides across it and grows when pressed (16 pixels off, 24 on, 28 pressed). The `Label` sits beside
the track and is part of what you press. With `Icons: true` the handle carries a check when on and a cross when off, and the off handle is then as big as the on one. Space or
Enter toggles it from the keyboard, and `Handlers { On_Change: ... }` runs after the user toggles it.

## How it is built

### `Switch`

A toggle.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Selected` | `bool` |  |  Two-way. |
| `Disabled` | `bool` |  |  |
| `Label` | `str` |  | Text beside it that is part of what you press, and what a screen reader calls it. |
| `Icons` | `bool` |  | A check on the handle when on and a cross when off. |

Its `Style` also takes `Foreground`.

## Using it

```tdl
Container {
  Name: settings
  Style { Flex_Direction: vertical, Gap: 8, Width: 240, Height: 140, Padding: 16 }
  Children {
    Switch {
      Selected: <| wifi |>
      Label: Wi-Fi
    }
    Switch {
      Selected: <| dark |>
      Label: "Dark mode"
      Icons: true
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import switch

dark = switch(app.window, selected=False)
```

## See also

- [Controls](../guide/controls.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
