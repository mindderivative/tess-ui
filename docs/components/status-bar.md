# Status bar

*Beyond MD3*

## In Material Design 3

Material Design 3 has no status bar. A desktop app often wants one, so this is a thin strip in MD3's
surface and *label* style.

## In Tesserae

`StatusBar` is a view Tesserae ships (`StatusBar_View.tdl`): a 24 pixel `surface_container` strip as wide as the place it is put in, with
`label_small` text in `on_surface_variant`.

Each of `Items` is `{Text}` and optionally `{Icon, Side, Value, Tooltip}`; `Side` is `start` (the default), `center` or `end`. `Text` (a string) is a shorthand for one message
at the start, and `Width` sets the bar's width instead of the place it is put in. `Progress` (0 to 1) shows a 4 pixel determinate indicator along the top edge, and `Busy`
one with no end. `Clicked` is two-way: the `Value` of the item last pressed.

An item with a `Value` is a button: it has a state layer, a tooltip if it has one, and pressing it sets `Clicked`. The centre section is centred on the
bar whatever the sides hold. The bar is announced politely when its items change. Not built: items that can be dragged or hidden when the window is
narrow.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `StatusBar { ... }`. A file of the same name in your project replaces it.

### `StatusBar`

A status bar (a desktop convention, not Material 3): a thin strip at the bottom of a window with short items on its left, centre and right. `Items` is a list of {text} and optionally {icon, side, value, tooltip}: `Side` is start (the default), center or end; an item with a `Value` can be pressed, and pressing it sets `Clicked` to the value; `Tooltip` explains it. `Progress` (0 to 1) or `Busy` shows a 4 pixel indicator along the top edge. The bar is announced politely when its text changes.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Text` | `str` |  | One message at the start, for a bar that only says one thing; the same as a first item {text}. |
| `Width` | `any` |  | The bar's width; the width of its place when not given. |
| `Items` | `list` | `[]` | The items, each {text} and optionally {icon, side, value, tooltip}. |
| `Progress` | `any` |  | 0 to 1: a determinate indicator along the top edge. Empty shows none. |
| `Busy` | `bool` | `false` | An indicator with no end along the top edge. |
| `Clicked` | `any` |  | The value of the item last pressed. Two-way: give it a bare reference and the view writes it back. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `section` (Container), `note` (Container), `note_icon` (Icon), `note_text` (Text), `item` (Container), `icon` (Icon), `text` (Text), `edge` (Container), `bar` (LinearProgress).

Its look is in [`StatusBar_Stylesheet.tdl`](../stylesheets/status-bar/status-bar.md).

## Using it

```tdl
Container {
  Name: editor
  Style { Flex_Direction: vertical, Width: 640, Height: 200 }
  Children {
    StatusBar {
      Clicked: <| item |>
      Busy: <| saving |>
      Items {
        Item { Text: Ready }
        Item { Text: Saved, Side: center }
        Item { Text: "Ln 4, Col 2", Side: end, Value: goto, Tooltip: "Go to line" }
        Item { Text: UTF-8, Side: end, Icon: home, Value: encoding }
      }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import status_bar

status = status_bar(app.window, "Ready", style={"height": 32})
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# StatusBar_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: StatusBar
    Part: text
    Style { Foreground: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Windows And Docks](../guide/windows-and-docks.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
