# Radio button

*Selection and input*

## In Material Design 3

A radio button lets the user choose one option from a set. Radio buttons in one group exclude each other,
and the arrow keys move between them.

## In Tesserae

`RadioButton`, a Tesserae control: a 20 pixel ring with a dot that grows in when it is chosen. Radio buttons with one `Group:` name share a group: choosing
one unchooses the others, the group is one Tab stop (the chosen one, else the first that is not disabled), and the arrow keys move the choice (and the focus) to the next or
previous button that is not disabled, wrapping round. A press on a chosen one does not unchoose it. The `Label` sits beside the ring and is part of what you press.

To keep the choice in one value, test it in `Selected` and set it in `On_Change`: `Selected: "<| size == 'm' |>"`, `On_Change: "size = 'm'"`.

## How it is built

### `RadioButton`

One choice of a group.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Selected` | `bool` |  |  Two-way. |
| `Group` | `str` |  | Buttons with one group are exclusive. |
| `Disabled` | `bool` |  |  |
| `Error` | `bool` |  | Drawn in the error colours. |
| `Label` | `str` |  | Text beside it that is part of what you press, and what a screen reader calls it. |

Its `Style` also takes `Foreground`.

## Using it

```tdl
Container {
  Name: sizes
  Style { Flex_Direction: vertical, Gap: 4, Width: 240, Height: 180, Padding: 16 }
  Children {
    RadioButton {
      Group: size
      Label: Small
      Selected: <| size == 's' |>
      Handlers {
        On_Change { Set { Target: size, Value: <| 's' |> } }
      }
    }
    RadioButton {
      Group: size
      Label: Medium
      Selected: <| size == 'm' |>
      Handlers {
        On_Change { Set { Target: size, Value: <| 'm' |> } }
      }
    }
    RadioButton {
      Group: size
      Label: Large
      Selected: <| size == 'l' |>
      Handlers {
        On_Change { Set { Target: size, Value: <| 'l' |> } }
      }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.controls import RadioGroup
from tess_ui.widgets import radio_button

group = RadioGroup()
small = radio_button(app.window, 48, selected=True, group=group)
```

## See also

- [Controls](../guide/controls.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
