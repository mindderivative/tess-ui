# Splitter

*Beyond MD3*

## In Material Design 3

Material Design 3 has no splitter. It divides the window into two panes with a bar the user drags.

## In Tesserae

`Splitter` has exactly two children, the panes, and a handle between them: a 16 pixel bar holding MD3's 4 by 48 drag handle, with a
resize cursor, a Tab stop, and the role of a slider for a screen reader.

`Orientation` puts the panes side by side (`horizontal`, the default) or one above the other (`vertical`). `Position`, from 0 to 1, is how much of the room the first
pane has, two-way: bind a Signal and the handle writes it. `Min_First` and `Min_Second` are the least each pane can be, in pixels. With `Collapsible: true` a double click
on the handle closes the first pane, and opens it again where it was. `Label` is what a screen reader calls the handle.

The pointer drags it (the pointer is captured, so it keeps following outside the handle); the arrow keys along its axis move it by 5%, Home
and End go to the ends; a screen reader can increment, decrement and set it. For more than two panes, nest splitters.

## How it is built

### `Splitter`

Two panes with a draggable, keyboard-operable handle between them.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Orientation` | `horizontal` or `vertical` | `horizontal` | horizontal puts the panes side by side, vertical one above the other. |
| `Position` | `float` | `0.5` | How much of the room the first pane has, from 0 to 1. Dragging the handle writes it back to a Signal it is bound to. Two-way. |
| `Min_First` | `float` |  | The least the first pane can be, in pixels. |
| `Min_Second` | `float` |  | The least the second pane can be, in pixels. |
| `Collapsible` | `bool` |  | A double click on the handle closes the first pane, and opens it again. |
| `Label` | `str` | `"Resize panes"` | What a screen reader calls the handle. |

## Using it

```tdl
Container {
  Name: editor
  Style { Width: 640, Height: 400 }
  Children {
    Splitter {
      Position: <| sidebar |>
      Min_First: 120
      Min_Second: 240
      Collapsible: true
      Label: "Resize the sidebar"
      Style { Width: 640, Height: 400 }
      Children {
        Container {
          Name: sidebar_pane
          Style { Background: surface_container, Flex: fill }
        }
        Container {
          Name: content_pane
          Style { Background: surface, Flex: fill }
        }
      }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import splitter

panes = splitter(app.window, left.node, right.node, 640, 400, orientation="horizontal", position=0.3)
```

## See also

- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
