# Tooltips

*Communication*

## In Material Design 3

A tooltip names or explains a control when the pointer rests on it, or it has keyboard focus.

## In Tesserae

Any node takes a `Tooltip:`. A plain one is text on the inverse surface; a rich one has a `Title`, up to two `Actions` and a `Placement`
(`below`, `above`, `start`, `end`, or a corner: `top_start`, `top_end`, `bottom_start`, `bottom_end`, `center`, which puts the middle of the tooltip on that point and is not flipped), is a raised surface the pointer can move onto, and closes when an action is pressed. It shows after the
pointer rests for `delay` (500 ms by default), at once on keyboard focus (focus that a click gave does not count), or after a touch held in place; Escape, a press, or leaving
closes it. The text also names the node for a screen reader, unless the node has a description of its own. Not built: reaching the actions by keyboard.

## Using it

```tdl
Container {
  Name: file
  Style { Width: 240, Height: 120, Padding: 24 }
  Children {
    Button {
      Label: Delete
      Tooltip { Title: Delete, Text: "Removes the file for good", Actions { Item { Label: Undo, On_Click: undo } } }
    }
    Button {
      Label: Save
      Variant: tonal
      Tooltip: "Save the file"
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import tooltip

tip = tooltip(app.window, "Save the file", anchor=save.node)
```

## See also

- [Overlays](../guide/overlays.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
